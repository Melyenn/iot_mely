from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route
from sqlalchemy.exc import IntegrityError

from backend.state import AppState
from backend.models import User

from .auth_service import authenticate, hash_create, logout
from .auth_service import hash_verify
from .auth_models import UserCreate, UserLogin


async def handle_register(request: Request) -> Response:
  state = AppState.get(request)
  with state.get_db() as db:
    try:
      payload = await request.json()
      user_create = UserCreate(**payload)
      password_hash = hash_create(user_create.password)
      user_db = User(
        email=user_create.email,
        password_hash=password_hash,
      )

      db.add(user_db)
      db.commit()
      db.refresh(user_db)

      return authenticate(user_db)
    except ValueError as e:
      return Response(str(e), status_code=400)
    except IntegrityError:
      db.rollback()
      return Response("Username or email already registered", status_code=400)


async def handle_login(request: Request) -> Response:
  state = AppState.get(request)
  with state.get_db() as db:
    try:
      payload = await request.json()
      user_login = UserLogin(**payload)

      user = db.query(User).filter(
        (User.email == user_login.email)
      ).first()

      if user is None:
        return Response("Invalid credentials", status_code=401)

      if not hash_verify(user_login.password, str(user.password_hash)):
        return Response("Invalid credentials", status_code=401)

      return authenticate(user)

    except ValueError as e:
      return Response(str(e), status_code=400)


async def handle_logout(_: Request) -> Response:
  return logout()


routes: list[BaseRoute] = [
  Route("/register", handle_register, methods=["POST"]),
  Route("/login", handle_login, methods=["POST"]),
  Route("/logout", handle_logout, methods=["POST"]),
]
