from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1 import api_router
from app.config import settings
from app.database import get_db

app = FastAPI(title="PitchPilot AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Registered most-specific-first: Starlette walks the raised exception's MRO
# and uses the first matching handler, so IntegrityError (a SQLAlchemyError
# subclass) is handled here, not by the broader handler below. Neither
# handler echoes the underlying exception text, which may contain table/
# column names, SQL fragments, or (for connection failures) parts of the
# connection string.
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "The request conflicts with existing data."})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Database unavailable."})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unreachable") from None
    return {"status": "ok", "service": settings.service_name, "database": "reachable"}
