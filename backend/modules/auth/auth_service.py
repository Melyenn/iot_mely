from jose import JWTError, jwt
from passlib.context import CryptContext
import datetime
from datetime import datetime, timedelta, timezone

from os import environ as env

from backend.models import User
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.state import AppState

secret_key = env.get("JWT_SECRET_KEY", default="secret-key")
token_expire_min = int(env.get("JWT_EXPIRE_MIN", default="30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_create(password: str) -> str:
  return pwd_context.hash(password)


def hash_verify(password: str, hash: str) -> bool:
  return pwd_context.verify(password, hash)


def create_access_token(data: dict, expires_delta: timedelta):
  """Create a JWT access token"""
  to_encode = data.copy()
  expire = datetime.now(timezone.utc) + expires_delta
  
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
  return encoded_jwt


def verify_token(token: str) -> str | None:
  """Verify and decode a JWT token"""
  try:
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    username = payload.get("sub")
    if username is None:
      return None
    return username
  except JWTError:
    return None


def authenticate(user: User) -> Response:
  access_token_expires = timedelta(minutes=token_expire_min)
  access_token = create_access_token(
    data={"sub": user.email}, 
    expires_delta=access_token_expires
  )

  response = JSONResponse({
    access_token: access_token,
  })

  response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    max_age=60 * token_expire_min,
    expires=60 * token_expire_min,
  )

  return response


def get_user(request: Request) -> User | None:
  state = AppState.get(request)
  with state.get_db() as db:
    token = request.cookies.get('access_token')

    if token is None:
      return None

    username = verify_token(token)
    if username is None:
      return None
    user = db.query(User).filter(User.email == username).first()

    if user is not None and bool(user.is_active):
      return user

  return None


def logout() -> Response:
  response = Response("success", status_code=200)
  response.delete_cookie(key="access_token")
  return response
