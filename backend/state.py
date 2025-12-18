from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from os import environ as env

from openai import OpenAI
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket
from backend.modules.websocket.websocket_service import broadcast_sensor_data

from backend.models import SensorData
from backend.models import Base

from datetime import datetime
from typing import cast

import paho.mqtt.client as paho
from paho.mqtt.client import Client

import json

import ssl


MQTT_HOST = env.get("MQTT_HOST", "localhost")
MQTT_PORT = int(env.get("MQTT_PORT", 8883))
MQTT_USER = env.get("MQTT_USER", "")
MQTT_PASS = env.get("MQTT_PASS", "")


def init_mqtt(client: Client) -> Client:
	def on_connect(client, userdata, flags, rc, properties=None) -> None:
		print("CONNACK received with code %s." % rc)

	client.on_connect = on_connect

	def on_publish(client, userdata, mid, properties=None) -> None:
		print("mid: " + str(mid))

	client.on_publish = on_publish

	def on_message(client, userdata, msg) -> None:
		payload_str = msg.payload.decode()
		data = json.loads(payload_str)
		temperature = data["temperature"]
		gas = data["gas"]
		if temperature is not None and gas is not None:
			print(f"Temperature: {temperature}, Gas: {gas}")
			timestamp = datetime.now()
			with userdata.get_db() as db:
				sensor_data = SensorData(
					timestamp=timestamp, temperature=temperature, gas=gas
				)
				db.add(sensor_data)
				db.commit()

			# Broadcast to WebSocket clients
			loop = userdata.main_loop
			asyncio.run_coroutine_threadsafe(
				broadcast_sensor_data(
					userdata,
					{
						"id": cast(int, sensor_data.id),
						"timestamp": timestamp.isoformat(),
						"temperature": temperature,
						"gas": gas,
					},
				),
				loop,
			)

	client.on_message = on_message

	client.tls_set(tls_version=ssl.PROTOCOL_TLS)

	client.username_pw_set(MQTT_USER, MQTT_PASS)
	client.connect(MQTT_HOST, MQTT_PORT)

	client.subscribe("sensor/response")

	client.loop_start()

	return client


def start_task(
	callback: Callable[[], Awaitable[None]], interval: float
) -> asyncio.Task[None]:
	async def task():
		while True:
			await callback()
			await asyncio.sleep(interval)

	return asyncio.create_task(task())


@dataclass
class AppState:
	db_engine: Engine
	session: sessionmaker[Session]
	openai_client: OpenAI

	ws_connections: set[WebSocket]

	mqtt_client: Client

	main_loop: asyncio.AbstractEventLoop

	sensor_task: asyncio.Task[None] | None = None

	@classmethod
	def init(cls, app: Starlette) -> AppState:
		db_url = env.get("DATABASE_URL", default="sqlite:///./data.db")
		connect_args = {}
		if db_url.startswith("sqlite"):
			connect_args = {"check_same_thread": False}

		engine = create_engine(db_url, connect_args=connect_args)

		Base.metadata.create_all(bind=engine)

		main_loop = asyncio.get_event_loop()

		state = cls(
			db_engine=engine,
			session=sessionmaker(
				autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
			),
			openai_client=OpenAI(),
			ws_connections=set(),
			mqtt_client=init_mqtt(paho.Client(client_id="", protocol=paho.MQTTv5)),
			main_loop=main_loop,
		)
		state.mqtt_client.user_data_set(state)

		app.state.data = state

		return state

	async def deinit(self) -> None:
		if self.sensor_task is not None:
			self.sensor_task.cancel()

		if self.ws_connections:
			await asyncio.gather(
				*(
					connection.close(code=1001, reason="Closing server")
					for connection in self.ws_connections
				)
			)

		self.db_engine.dispose()

	@contextmanager
	def get_db(self) -> Generator[Session]:
		db = self.session()
		try:
			yield db
			db.commit()
		except Exception:
			db.rollback()
			raise
		finally:
			db.close()

	@staticmethod
	def get(request: HTTPConnection) -> AppState:
		return request.app.state.data
