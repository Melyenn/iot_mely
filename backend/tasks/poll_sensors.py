import asyncio
import random
from datetime import datetime

from backend.models import SensorData
from backend.modules.websocket.websocket_service import broadcast_sensor_data
from backend.state import AppState


async def fetch_sensor_data() -> tuple[float, float]:
	"""
	Fetch sensor data from the hardware.
	Currently returns random data for testing purposes.
	Replace this function with actual sensor reading logic when ready.

	Returns:
		tuple[float, float]: (temperature, gas) readings
	"""
	# Simulate async sensor reading
	await asyncio.sleep(0.1)

	# Generate random sensor data
	temperature = round(random.uniform(18.0, 30.0), 2)
	gas = round(random.uniform(300.0, 500.0), 2)

	return temperature, gas


async def poll_sensors(state: AppState) -> None:
	"""
	Poll sensors and store the data in the database.
	This function is called periodically by the sensor task.
	"""
	temperature, gas = await fetch_sensor_data()
	timestamp = datetime.now()

	with state.get_db() as db:
		sensor_data = SensorData(timestamp=timestamp, temperature=temperature, gas=gas)
		db.add(sensor_data)
		db.commit()

	# Broadcast to WebSocket clients
	await broadcast_sensor_data(
		state,
		{
			"id": int(sensor_data.id),
			"timestamp": timestamp.isoformat(),
			"temperature": temperature,
			"gas": gas,
		},
	)
