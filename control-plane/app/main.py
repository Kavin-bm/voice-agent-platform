from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.services.dograh_client import DograhClientError

app = FastAPI(title="Voice Agent Platform — Control Plane")
app.include_router(api_router)


@app.exception_handler(DograhClientError)
async def dograh_client_error_handler(request: Request, exc: DograhClientError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
