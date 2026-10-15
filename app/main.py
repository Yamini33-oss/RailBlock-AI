"""KAVACH BIE (Block Intelligence Engine) — Member 3 Main Application.

FastAPI backend orchestrating:
- AI maintenance block planning & Google OR-Tools CP-SAT optimization
- Real Indian Railways data pipeline (8.9k stations, 5.2k trains, 417k schedules)
- Firebase Authentication, Cloud Firestore, Cloud Storage, and Cloud Messaging
- Integration endpoints for Member 2 (Delay Prediction) and Member 4 (Conflict Validation)
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_data import router as data_router
from app.api.routes_health import router as health_router
from app.api.routes_maintenance import router as maintenance_router
from app.api.routes_optimization import router as optimization_router
from app.config import settings
from optimizer.api import optimizer_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kavach_bie_member3")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    logger.info("=" * 70)
    logger.info("Starting KAVACH BIE — Member 3 Engine")
    logger.info("Environment: %s | Default Timezone: %s", settings.ENVIRONMENT, settings.DEFAULT_TIMEZONE)
    logger.info("Firebase Configured: %s | Mock Firebase: %s", settings.is_firebase_configured, settings.MOCK_FIREBASE)
    logger.info("Processed Data Directory: %s", settings.DATA_PROCESSED_DIR)
    logger.info("=" * 70)
    yield
    logger.info("Shutting down KAVACH BIE — Member 3 Engine.")


app = FastAPI(
    title="KAVACH BIE — Member 3: AI Block Planning & Optimization Engine",
    description=(
        "Core optimization, real railway data engineering, and Firebase integration module "
        "for railway maintenance block scheduling under Problem Statement SIH26027."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 REST Routers
app.include_router(health_router)
app.include_router(data_router)
app.include_router(maintenance_router)
app.include_router(optimization_router)

# Include core optimizer router for Member 5 direct contract compatibility
app.include_router(optimizer_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception at %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": str(exc),
            "path": request.url.path,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
