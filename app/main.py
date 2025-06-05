from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import process


def create_app():
    app = FastAPI(
        title="Gestión de Desperdicios",
        version="1.0.0",
        description="API para analizar métricas de desperdicio y predecir demanda óptima."
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins = ["*"],
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"],
    )
    
    app.include_router(process.router, prefix="/api/v1/process", tags=["Process"])
    return app


app = create_app()