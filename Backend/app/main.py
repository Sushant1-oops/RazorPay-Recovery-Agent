"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, get_logger, new_request_id
from app.core.database import engine, Base
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.webhooks import router as webhook_router
from app.api.routes.payments import router as payments_router
from app.api.routes.recoveries import router as recoveries_router
from app.api.routes.analytics import router as analytics_router
from app.core.exceptions import WebhookSignatureError

setup_logging(debug=settings.DEBUG)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_starting", env=settings.APP_ENV)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")
    yield
    logger.info("application_shutting_down")


app = FastAPI(
    title="Payment Recovery Agent",
    description="Razorpay webhook-driven agent that recovers failed payments",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(payments_router)
app.include_router(recoveries_router)
app.include_router(analytics_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = new_request_id()
    import structlog

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(WebhookSignatureError)
async def webhook_signature_handler(request: Request, exc: WebhookSignatureError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
