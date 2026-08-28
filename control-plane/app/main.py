from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.dograh_client import DograhClientError

settings = get_settings()

app = FastAPI(title="Voice Agent Platform — Control Plane")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.dashboard_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(DograhClientError)
async def dograh_client_error_handler(request: Request, exc: DograhClientError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
