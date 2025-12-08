from starlette.routing import BaseRoute, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from backend.modules.auth.auth_service import get_user
from backend.state import AppState


async def websocket_endpoint(websocket: WebSocket) -> None:
	"""
	WebSocket endpoint for real-time sensor data updates.
	Uses cookie-based authentication.
	"""
	await websocket.accept()

	# Authenticate user
	user = get_user(websocket)
	if user is None:
		await websocket.close(code=1008, reason="Unauthorized")
		return

	# Get app state and register connection
	state = AppState.get(websocket)
	state.ws_connections.add(websocket)

	try:
		# Keep connection alive and listen for close
		while True:
			# Wait for any message (we don't process them, just keep alive)
			await websocket.receive_text()
	except WebSocketDisconnect:
		# Remove connection when closed
		state.ws_connections.discard(websocket)
	except Exception as e:
		print(f"WebSocket error: {e}")
		state.ws_connections.discard(websocket)


routes: list[BaseRoute] = [WebSocketRoute("/ws", websocket_endpoint)]
