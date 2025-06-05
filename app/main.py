from fastapi import FastAPI
from app.routers import process


def create_app():
    app = FastAPI(
        title="Gestión de Desperdicios",
        version="1.0.0",
        description="API para analizar métricas de desperdicio y predecir demanda óptima."
    )
    
    app.include_router(process.router, prefix="/api/v1/process", tags=["Process"])
    return app


app = create_app()