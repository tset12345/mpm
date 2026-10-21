import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.ratelimit import ip_rate_limit
from app.core.request_context import request_id_var
from app.routers import stocks, holdings, profiles, portfolio, analysis, virtual, market, system
from app.services.scheduler import start_scheduler, scheduler

setup_logging()
logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_scheduler or settings.enable_intraday:
        start_scheduler()
    yield
    if settings.enable_scheduler or settings.enable_intraday:
        scheduler.shutdown()
    from app.services.kis_api import kis_client
    await kis_client.aclose()
    from app.routers.market import _YAHOO_CLIENT
    if _YAHOO_CLIENT and not _YAHOO_CLIENT.is_closed:
        await _YAHOO_CLIENT.aclose()


app = FastAPI(title="MPM API", version="2.0.0-dev", lifespan=lifespan, dependencies=[Depends(ip_rate_limit)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list({o.strip() for o in settings.allowed_origins.split(",") if o.strip()} | {
        "http://localhost:3000",
        "https://mpm-fe.vercel.app",
    }),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    token = request_id_var.set(request_id)
    try:
        logging.getLogger("app.errors").error(
            "처리되지 않은 예외 %s %s", request.method, request.url.path, exc_info=exc
        )
    finally:
        request_id_var.reset(token)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        if request.url.path != "/api/v1/health":
            logger.info("%s %s %.0fms", request.method, request.url.path, elapsed_ms)
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(stocks.router)
app.include_router(holdings.router)
app.include_router(profiles.router)
app.include_router(portfolio.router)
app.include_router(analysis.router)
app.include_router(virtual.router)
app.include_router(market.router)
app.include_router(system.router)


@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}
