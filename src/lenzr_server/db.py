import os
from contextlib import asynccontextmanager
from typing import Any

import fastapi
from sqlalchemy import create_engine

from lenzr_server import models


def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        sqlite_file_name = "/tmp/lenzr_server_db.sqlite3"
        sqlite_url = f"sqlite:///{sqlite_file_name}"
        db_url = sqlite_url

    return db_url


def get_connect_args(db_url: str) -> dict[str, Any]:
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    else:
        return {}


database_url = get_database_url()
connect_args = get_connect_args(database_url)
engine = create_engine(database_url, connect_args=connect_args)


@asynccontextmanager
async def db_lifetime(_app: fastapi.FastAPI):
    models.SQLModel.metadata.create_all(engine)
    yield
    if os.getenv("ENVIRONMENT") == "development":
        models.SQLModel.metadata.drop_all(engine)
