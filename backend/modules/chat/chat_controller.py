from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route

from backend.modules.auth.auth_service import get_user
from backend.modules.chat.chat_models import ChatRequest, ChatResponse
from backend.modules.chat.chat_service import chat
from backend.state import AppState


def strip_prefix(text: str, prefix: str) -> str:
	"""Remove prefix from text if present, otherwise return text unchanged."""
	if text.startswith(prefix):
		return text[len(prefix) :]
	return text


async def handle_chat(request: Request) -> Response:
	user = get_user(request)
	if user is None:
		return Response(status_code=401)

	try:
		payload = await request.json()
		chat_request = ChatRequest(**payload)

		state = AppState.get(request)
		messages_dict = [msg.model_dump() for msg in chat_request.messages]
		new_messages = chat(state, messages_dict)

		response = ChatResponse(messages=new_messages)
		return JSONResponse(response.model_dump())

	except ValidationError as e:
		first_error = e.errors()[0]
		error_msg = first_error.get("msg", str(e))
		error_msg = strip_prefix(error_msg, "Value error, ")
		return Response(error_msg, status_code=400)


routes: list[BaseRoute] = [
	Route("/", handle_chat, methods=["POST"]),
]
