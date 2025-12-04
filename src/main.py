from collections.abc import Coroutine
from contextlib import asynccontextmanager
from os import environ as env
from typing import Any, Callable
from state import AppState
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import aiofiles
import uvicorn

from modules.auth import auth_controller

def homepage_handler(dev: bool) -> Callable[[Request], Coroutine[Any, Any, Response]]:
  if dev:
    async def handler(_: Request) -> Response:
      async with aiofiles.open("frontend/index.html") as f:
        data = await f.read()

      return Response(data, media_type="text/html")

    return handler

  with open("frontend/index.html") as f:
    data = f.read()

  response = Response(data, media_type="text/html")

  async def handler(_: Request) -> Response:
    return response

  return handler

dev = env.get('DEV') is not None
port = int(env.get('PORT', default='3000'))
host = env.get('HOST', default='0.0.0.0')

@asynccontextmanager
async def lifespan(app: Starlette):
  AppState.init(app)
  yield

app = Starlette(routes=[
  Route("/", homepage_handler(dev), methods=["GET"]),
  Mount("/static", StaticFiles(directory="frontend/static"), name="static"),
  Mount("/auth", routes=auth_controller.routes)
], lifespan=lifespan)

if __name__ == '__main__':
  if dev:
    uvicorn.run('main:app', host='127.0.0.1', port=port, reload=True)
  else:
    uvicorn.run(app, host=host, port=port) 
