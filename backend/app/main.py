from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog
import asyncio

from app.core.config import settings
from app.core.logging import setup_logging
from app.domain.exceptions import TenderNotFoundException, TenderAlreadyExistsException, TenderNotParsedException
from app.api.routers.tenders import router as tenders_router
from app.api.routers.imports import router as imports_router
from app.api.routers.documents import router as documents_router
from app.api.routers.metadata import router as metadata_router
from app.api.routers.boq import router as boq_router
from app.api.routers.boq_analytics import router as boq_analytics_router
from app.api.routers.projects import router as projects_router
from app.api.routers.matching import router as matching_router
from app.api.routers.qualification import router as qualification_router
from app.api.routers.risk import router as risk_router
from app.api.routers.recommendation import router as recommendation_router
from app.api.routers.analyst import router as analyst_router
from app.api.routers.reviews import router as reviews_router
from app.core.observability import setup_observability
from app.api.routers.telemetry import router as telemetry_router
from app.api.routers.auth import router as auth_router
from app.api.routers.admin import router as admin_router
from app.workers.download_worker import start_worker, stop_worker





# Setup structured logging
setup_logging()
logger = structlog.get_logger("app.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize observability metrics, Sentry, and OpenTelemetry
setup_observability(app)


# CORS configuration
frontend_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(TenderNotFoundException)
async def tender_not_found_exception_handler(
    request: Request, exc: TenderNotFoundException
):
    logger.warn("Tender not found", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(TenderAlreadyExistsException)
async def tender_already_exists_exception_handler(
    request: Request, exc: TenderAlreadyExistsException
):
    logger.warn("Tender conflict", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(TenderNotParsedException)
async def tender_not_parsed_exception_handler(
    request: Request, exc: TenderNotParsedException
):
    logger.warn("Tender not parsed", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Uncaught server exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Include API routers
app.include_router(tenders_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(metadata_router, prefix="/api/v1")
app.include_router(boq_router, prefix="/api/v1")
app.include_router(boq_analytics_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(matching_router, prefix="/api/v1")
app.include_router(qualification_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(recommendation_router, prefix="/api/v1")
app.include_router(analyst_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")






@app.on_event("startup")
async def startup_event():
    # Start download worker in non-test environments
    if settings.ENV != "test":
        start_worker(interval_seconds=15)
        logger.info("Application worker started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    if settings.ENV != "test":
        stop_worker()
        logger.info("Application worker stopped successfully")


@app.get("/health", status_code=status.HTTP_200_OK, tags=["monitoring"])
async def health_check():
    """Simple API health check endpoint."""
    return {"status": "healthy", "project": settings.PROJECT_NAME}
