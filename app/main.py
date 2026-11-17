from contextlib import asynccontextmanager
import struct

from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
import logging

from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}",
    pool_pre_ping=True,
)
credential = DefaultAzureCredential()


@event.listens_for(engine, "do_connect")
def add_access_token(dialect, conn_record, cargs, cparams):
    token = credential.get_token("https://database.windows.net/.default").token
    token_bytes = token.encode("utf-16-le")
    cparams["attrs_before"] = {
        1256: struct.pack("=i", len(token_bytes)) + token_bytes
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = engine
    yield
    app.state.engine.dispose()


app = FastAPI(title="SWIFBAC StateInfo API", version="1.0.0", lifespan=lifespan)


def query_states(sql: str, params: dict | None = None):
    try:
        with app.state.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row) for row in result.mappings().all()]
    except SQLAlchemyError:
        logger.exception("Database query failed")
        raise HTTPException(status_code=503, detail="Database query failed")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/api/states/GetAll", tags=["States"])
def get_all():
    return query_states("SELECT * FROM dbo.StateInfo")


@app.get("/api/states/GetAllByPopulation", tags=["States"])
def get_all_by_population(populationCount: int = Query(..., ge=0)):
    return query_states("SELECT * FROM dbo.StateInfo WHERE Population >= :populationCount",
                        {"populationCount": populationCount})


@app.get("/api/states/GetByCode", tags=["States"])
def get_by_code(stateCode: str = Query(..., min_length=1)):
    return query_states("SELECT * FROM dbo.StateInfo WHERE StateCode = :stateCode",
                        {"stateCode": stateCode})


@app.get("/api/states/GetByName", tags=["States"])
def get_by_name(stateName: str = Query(..., min_length=1)):
    return query_states("SELECT * FROM dbo.StateInfo WHERE StateName = :stateName",
                        {"stateName": stateName})


@app.get("/info", tags=["Information"])
async def get_info():
    return {
        "name": "StateInfo WebAPI",
        "description": (
            "StateInfo WebAPI is a RESTful service built using "
            "Python and FastAPI. It provides access to "
            "information about U.S. states through HTTP endpoints. "
            "The API is designed to be lightweight, scalable, "
            "and easy to integrate with other applications."
        ),
        "version": "1.0.0",
        "status": "active"
    }
