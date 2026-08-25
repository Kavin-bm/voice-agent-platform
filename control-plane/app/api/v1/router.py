from fastapi import APIRouter

from app.api.v1 import auth, businesses, credentials, tenants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(credentials.router)
api_router.include_router(businesses.router)
