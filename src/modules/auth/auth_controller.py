from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route
from sqlalchemy.exc import IntegrityError

from ...state import AppState
from ...models import User
from auth_models import UserCreate

from jose import JWTError, jwt
from passlib.context import CryptContext
import datetime
from datetime import datetime, timedelta, timezone

from os import environ as env

secret_key = env.get("JWT_SECRET_KEY", default="secret-key")
token_expire_min = int(env.get("JWT_EXPIRE_MIN", default="30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta):
  """Create a JWT access token"""
  to_encode = data.copy()
  expire = datetime.now(timezone.utc) + expires_delta
  
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
  return encoded_jwt

async def handle_register(request: Request) -> Response:
  state = AppState.get(request)
  with state.get_db() as db:
    payload = await request.json()
    try:
      user_create = UserCreate(**payload)
      password_hash = pwd_context.hash(user_create.password)
      user_db = User(
        email=user_create.email,
        password_hash=password_hash,
      )

      db.add(user_db)
      db.commit()
      db.refresh(user_db)

      access_token_expires = timedelta(minutes=token_expire_min)
      access_token = create_access_token(
        data={"sub": user_db.email}, 
        expires_delta=access_token_expires
      )
      return JSONResponse({
        access_token: access_token,
      })
    except ValueError as e:
      return Response(str(e), status_code=400)
    except IntegrityError:
      db.rollback()
      return Response("Username or email already registered", status_code=400)

routes: list[BaseRoute] = [
  Route("/register", handle_register)
]
