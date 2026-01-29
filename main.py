from fastapi import FastAPI

from contextlib import asynccontextmanager
from database.initialize import create_db_and_tables



@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="Projet Fil Rouge",
    lifespan=lifespan,
)


@app.get("/")
def greet():
    return {"hello": "world"}