from __future__ import annotations
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from os import environ as env

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket

from backend.models import Base


import asyncio
from collections.abc import Awaitable, Callable


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

	ws_connections: dict[str, WebSocket]

	sensor_task: asyncio.Task[None] | None = None

	@classmethod
	def init(cls, app: Starlette) -> AppState:
		db_url = env.get("DATABASE_URL", default="sqlite:///./data.db")
		connect_args = {}
		if db_url.startswith("sqlite"):
			connect_args = {"check_same_thread": False}

		engine = create_engine(db_url, connect_args=connect_args)

		Base.metadata.create_all(bind=engine)

		state = cls(
			db_engine=engine,
			session=sessionmaker(
				autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
			),
			ws_connections=dict(),
		)

		app.state.data = state
		return state

	async def deinit(self) -> None:
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
