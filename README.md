# SWIFBAC StateInfo FastAPI

FastAPI endpoints backed by Microsoft SQL Server `swifbacdb.dbo.StateInfo`.

## Prerequisites
- Python 3.10+
- Microsoft ODBC Driver 18 for SQL Server installed locally
- Network access to the SQL Server host; SQL Server login authorized to SELECT from `dbo.StateInfo`
- A trusted SQL Server TLS certificate (ODBC Driver 18 defaults to encryption and certificate validation)

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and replace DB_PASSWORD with your actual password.
uvicorn app.main:app --reload
```

On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`.

Swagger UI: http://127.0.0.1:8000/docs

## Routes
- `GET /api/states/GetAll`
- `GET /api/states/GetAllByPopulation?populationCount=5000000`
- `GET /api/states/GetByCode?stateCode=IL`
- `GET /api/states/GetByName?stateName=Illinois`
- `GET /health`

Responses are JSON arrays of database rows, with original SQL column names. No rows returns `[]`. Query validation errors return 422; database errors return 503 without exposing credentials or internal details.

Queries use SQLAlchemy bind parameters, translated to ODBC parameter binding, not string interpolation. The application does not create or modify database tables.

## Example
```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/states/GetByCode?stateCode=IL'
```

## Security
Never commit `.env` to Git. Because the password was shared in chat, consider rotating the SQL login password before deploying. In production, store it in a managed secret store and avoid using `--reload`. Limit database permissions to SELECT on `dbo.StateInfo`.
