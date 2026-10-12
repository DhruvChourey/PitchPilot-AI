from fastapi import APIRouter

from app.api.v1.leads import router as leads_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(leads_router)
