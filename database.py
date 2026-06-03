import os

from sqlmodel import Session, create_engine

DATABASE_PATH = os.environ.get("DATABASE_PATH", "scubaduikers.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    with Session(engine) as session:
        yield session
