"""netlab-platform API — FastAPI application entrypoint."""

import asyncio
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1 import auth, console, grading, images, instructor, labs
from app.console.proxy import console_websocket
from app.core.config import settings
from app.core.logging import new_request_id, setup_logging
from app.db.base import Base
from app.db.models import Grade, LabProgress, LabSession, NodeImage, User  # noqa: F401
from app.db.session import SessionLocal, engine
from app.labs.manager import LabManager

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="netlab-platform API",
    version="0.1.0",
    description="Browser-based network lab platform with real Containerlab emulation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = new_request_id()
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.monotonic() - started) * 1000,
    )
    return response


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(labs.router, prefix="/api/v1/labs", tags=["labs"])
app.include_router(console.router, prefix="/api/v1/labs", tags=["console"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
app.include_router(grading.router, prefix="/api/v1/labs", tags=["grading"])
app.include_router(
    instructor.router, prefix="/api/v1/instructor", tags=["instructor"]
)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/console/{session_id}/{node}")
async def console_ws(websocket, session_id: str, node: str):
    observer = websocket.query_params.get("observer") == "1"
    await console_websocket(websocket, session_id, node, observer=observer)


async def _reaper_loop() -> None:
    """Background task: destroy expired sessions every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            LabManager(db).reap_expired()
        except Exception as exc:  # the reaper must never crash the app
            logger.warning("reaper error: %s", exc)
        finally:
            db.close()


@app.on_event("startup")
async def on_startup():
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        logger.info("database tables ensured")
    asyncio.create_task(_reaper_loop())
    logger.info("netlab API started (labs_dir=%s)", settings.labs_dir)
