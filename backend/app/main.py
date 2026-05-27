import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.routers import stocks, holdings, profiles, portfolio, analysis
from app.services.scheduler import start_scheduler, scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[startup] enable_scheduler={settings.enable_scheduler}")
    if settings.enable_scheduler:
        start_scheduler()
    yield
    if settings.enable_scheduler:
        scheduler.shutdown()


app = FastAPI(title="MPM API", version="1.0.0", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(holdings.router)
app.include_router(profiles.router)
app.include_router(portfolio.router)
app.include_router(analysis.router)


@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}
