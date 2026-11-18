
from contextlib import asynccontextmanager
import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError


# --------------------------------------------------
# Logging and environment configuration
# --------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# SQL Server configuration
# --------------------------------------------------

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

required_vars = {
    "DB_SERVER": server,
    "DB_NAME": database,
    "DB_USER": username,
    "DB_PASSWORD": password,
}

missing_vars = [
    name for name, value in required_vars.items()
    if not value
]

if missing_vars:
    raise RuntimeError(
        "Missing required environment variables: "
        + ", ".join(missing_vars)
    )


# --------------------------------------------------
# SQL Server connection string
# SQL Server Authentication (UID / PWD)
# No Azure access token required
# --------------------------------------------------

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


# --------------------------------------------------
# SQLAlchemy engine
# --------------------------------------------------

connection_url = URL.create(
    "mssql+pyodbc",
    query={
        "odbc_connect": connection_string
    }
)

engine = create_engine(
    connection_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)


# --------------------------------------------------
# FastAPI application lifecycle
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = engine

    logger.info("StateInfo API started")

    yield

    app.state.engine.dispose()

    logger.info("StateInfo API stopped")


app = FastAPI(
    title="SWIFBAC StateInfo API",
    version="1.0.0",
    lifespan=lifespan
)


# --------------------------------------------------
# Database query helper
# --------------------------------------------------

def query_states(sql: str, params: dict | None = None):
    try:
        with app.state.engine.connect() as conn:
            result = conn.execute(
                text(sql),
                params or {}
            )

            return [
                dict(row)
                for row in result.mappings().all()
            ]

    except SQLAlchemyError:
        logger.exception("Database query failed")

        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok"
    }


# --------------------------------------------------
# State endpoints
# --------------------------------------------------

@app.get("/api/states/GetAll", tags=["States"])
def get_all():
    return query_states(
        "SELECT * FROM dbo.StateInfo"
    )


@app.get("/api/states/GetAllByPopulation", tags=["States"])
def get_all_by_population(
    populationCount: int = Query(..., ge=0)
):
    return query_states(
        """
        SELECT *
        FROM dbo.StateInfo
        WHERE Population >= :populationCount
        """,
        {
            "populationCount": populationCount
        }
    )


@app.get("/api/states/GetByCode", tags=["States"])
def get_by_code(
    stateCode: str = Query(..., min_length=1)
):
    return query_states(
        """
        SELECT *
        FROM dbo.StateInfo
        WHERE StateCode = :stateCode
        """,
        {
            "stateCode": stateCode
        }
    )


@app.get("/api/states/GetByName", tags=["States"])
def get_by_name(
    stateName: str = Query(..., min_length=1)
):
    return query_states(
        """
        SELECT *
        FROM dbo.StateInfo
        WHERE StateName = :stateName
        """,
        {
            "stateName": stateName
        }
    )


# --------------------------------------------------
# API information endpoint
# --------------------------------------------------

@app.get("/info", tags=["Information"])
async def get_info():
    return {
        "name": "StateInfo WebAPI",
        "description": (
            "StateInfo WebAPI is a RESTful service built using "
            "Python and FastAPI. It provides access to "
            "information about U.S. states through HTTP endpoints. "
            "The API is designed to be lightweight, scalable, "
            "and easy to integrate with other applications. "
            "This will be hosted on an MCP Server. CI/CD test."
        ),
        "version": "1.0.0",
        "status": "active"
    }
