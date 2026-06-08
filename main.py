import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from logging.handlers import RotatingFileHandler

import migrate
import models  # noqa: F401  # registers tables in SQLModel.metadata
from database import engine
from routers import pages, users
from routers.clubs import router as clubs_router
from routers.dives import router as dives_router


# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Console output
        RotatingFileHandler(
            "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=1
        )
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application and running migrations...")
    SQLModel.metadata.create_all(engine)
    migrate.run(engine)
    yield


def get_version() -> str:
    """Extract version from pyproject.toml"""
    with open("pyproject.toml") as f:
        for line in f:
            if line.startswith("version"):
                return line.split("=")[1].strip().strip('"\'')
    return "unknown"


app = FastAPI(
    lifespan=lifespan,
    version=get_version()
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
    max_age=None,
    same_site="strict",
    https_only=True,
)

ENVIRONMENT = os.environ.get("ENVIRONMENT", "PRD")
logger.info(f"Running in {ENVIRONMENT} environment")
if ENVIRONMENT.upper() == "DEV":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # prd
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://scubaduikers.nl", "https://www.scubaduikers.nl"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["scubaduikers.nl", "www.scubaduikers.nl"],
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(users.router)
app.include_router(clubs_router)
app.include_router(dives_router)
