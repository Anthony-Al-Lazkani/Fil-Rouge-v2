from sqlmodel import Session

from database.initialize import engine


def get_session():
    with Session(engine) as session:
        yield session