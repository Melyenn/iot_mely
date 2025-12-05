from __future__ import annotations
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from starlette.applications import Starlette
from starlette.requests import Request

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from os import environ as env

from backend.models import Base

@dataclass
class AppState:
  db_engine: Engine
  session: sessionmaker

  @classmethod
  def init(cls, app: Starlette):
    db_url = env.get("DATABASE_URL", default="sqlite:///./data.db")
    db_engine = create_engine(db_url)

    Base.metadata.create_all(bind=db_engine)

    app.state.data = cls(
      db_engine = db_engine,
      session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine),
    )

  @contextmanager
  def get_db(self) -> Generator[Session]:
    db = self.session()
    try:
      yield db
    finally:
      db.close()

  @staticmethod
  def get(request: Request) -> AppState:
    return request.app.state.data
