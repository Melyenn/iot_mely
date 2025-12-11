from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Mount, Route

from backend.modules.auth.auth_service import get_user
from backend.modules.dashboard.dashboard_service import get_sensor_data
from backend.modules.dashboard.poll_control import poll_control_controller
from backend.state import AppState


async def handle_dashboard(request: Request) -> Response:
	user = get_user(request)
	if user is None:
		return Response(status_code=401)

	state = AppState.get(request)
	sensor_data = get_sensor_data(state, days=3)

	return JSONResponse(
		{
			"username": user.email,
			"sensor_data": [
				{
					"id": datapoint.id,
					"timestamp": datapoint.timestamp.isoformat(),
					"temperature": datapoint.temperature,
					"gas": datapoint.gas,
				}
				for datapoint in sensor_data
			],
		}
	)


routes: list[BaseRoute] = [
	Route("/", handle_dashboard, methods=["GET"]),
	Mount("/poll", routes=poll_control_controller.routes),
]
