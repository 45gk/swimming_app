from fastapi import APIRouter

from app.api.routes import health, imports, swimming

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(imports.router)
api_router.include_router(swimming.router)
