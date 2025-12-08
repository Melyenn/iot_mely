import asyncio
import json
from typing import TypedDict

from backend.state import AppState


class SensorDataDict(TypedDict):
	id: int
	timestamp: str
	temperature: float
	gas: float


async def broadcast_sensor_data(state: AppState, data: SensorDataDict) -> None:
	"""
	Broadcast sensor data to all connected WebSocket clients.
	Removes closed connections from the set.
	"""
	if not state.ws_connections:
		return

	message = json.dumps(data)

	# Gather all send operations
	results = await asyncio.gather(
		*(connection.send_text(message) for connection in state.ws_connections),
		return_exceptions=True,
	)

	# Remove connections that failed
	closed_connections = []
	for connection, result in zip(state.ws_connections, results):
		if isinstance(result, Exception):
			print(f"Failed to send to WebSocket: {result}")
			closed_connections.append(connection)

	# Remove closed connections
	for connection in closed_connections:
		state.ws_connections.discard(connection)
