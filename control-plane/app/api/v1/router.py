from fastapi import APIRouter

from app.api.v1 import agents, auth, businesses, credentials, knowledge, templates, tenants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(credentials.router)
api_router.include_router(businesses.router)
api_router.include_router(templates.router)
api_router.include_router(agents.router)
api_router.include_router(knowledge.router)
