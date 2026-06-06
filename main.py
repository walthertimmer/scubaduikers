import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware

import migrate
import models  # noqa: F401  # registers tables in SQLModel.metadata
from database import engine
from routers import pages, users
from routers.clubs import router as clubs_router
from routers.dives import router as dives_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    migrate.run(engine)
    yield


def get_version() -> str:
    with open("pyproject.toml") as f:
        for line in f:
            if line.startswith("version"):
                return line.split("=")[1].strip().strip('"\'')
    return "unknown"


app = FastAPI(
    lifespan=lifespan,
    version=get_version())

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(users.router)
app.include_router(clubs_router)
app.include_router(dives_router)
