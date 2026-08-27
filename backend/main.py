"""
NaviX FastAPI application entrypoint.

Wires together the database, every router, the WebSocket endpoint, and the
static frontend (a plain multi-page HTML/CSS/JS app -- see ../frontend).
Run from the `navix/` project root with:

    uvicorn backend.main:app --reload
"""
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import simulator
from .config import APP_VERSION, CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .routers import (
    admin,
    announcements,
    authorities,
    auth,
    devices,
    dispatches,
    emergencies,
    facilities,
    gateways,
    lost_persons,
    navigation,
    routes,
    volunteers,
)
from .schemas import HealthOut
from .seed import seed_if_empty
from .websocket_manager import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("navix")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(
    title="NaviX API",
    description="Emergency communication, navigation and coordination system for large public gatherings. "
    "Connecting Every Step, Even Without Networks.",
    version=APP_VERSION,
)

# Wide-open CORS in dev so the frontend can be opened from any origin while
# testing; set CORS_ORIGINS to specific origins before a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers, grouped by domain (spec section 27/46)
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(facilities.router)
app.include_router(routes.router)
app.include_router(volunteers.router)
app.include_router(devices.router)
app.include_router(gateways.router)
app.include_router(gateways.message_router)
app.include_router(emergencies.router)
app.include_router(announcements.router)
app.include_router(lost_persons.router)
app.include_router(authorities.router)
app.include_router(dispatches.router)
app.include_router(navigation.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    logger.info("NaviX backend ready.")


@app.get("/api/health", response_model=HealthOut, tags=["System"])
def health_check() -> HealthOut:
    """Simple liveness/readiness probe (spec section 76). Exposes nothing
    secret -- just enough for a demo/monitoring check."""
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "error"
    return HealthOut(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        websocket_connections=manager.connection_count(),
        simulation_running=simulator.is_running(),
        version=APP_VERSION,
    )


# ---------------------------------------------------------------------------
# WebSocket -- one shared channel for all live updates (spec section 16)
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Clients don't need to send anything; we just keep the socket
            # open and listen for disconnects. Any inbound text is ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Static assets: uploaded lost-person photos + frontend css/js/icons/i18n
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/icons", StaticFiles(directory=os.path.join(FRONTEND_DIR, "icons")), name="icons")
app.mount("/i18n", StaticFiles(directory=os.path.join(FRONTEND_DIR, "i18n")), name="i18n")


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"))


@app.get("/service-worker.js", include_in_schema=False)
def service_worker():
    # Served from the root path (not under /js) so its scope covers the
    # whole origin -- required for it to intercept navigation requests.
    return FileResponse(os.path.join(FRONTEND_DIR, "service-worker.js"), media_type="application/javascript")


@app.get("/offline.html", include_in_schema=False)
def offline_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "offline.html"))


# ---------------------------------------------------------------------------
# Frontend page routes (spec section 21) -- a plain multi-page app, each
# clean URL maps to one static HTML file under frontend/pages/.
# ---------------------------------------------------------------------------
PAGE_ROUTES = {
    "/": "index.html",
    "/find-help": "find-help.html",
    "/navigation": "navigation.html",
    "/sos": "sos.html",
    "/alerts": "alerts.html",
    "/lost-person": "lost-person.html",
    "/lost-person/report": "lost-person-report.html",
    "/facilities": "facilities.html",
    "/volunteer/login": "volunteer-login.html",
    "/volunteer/dashboard": "volunteer-dashboard.html",
    "/admin/login": "admin-login.html",
    "/admin/dashboard": "admin-dashboard.html",
    "/admin/emergencies": "admin-emergencies.html",
    "/admin/volunteers": "admin-volunteers.html",
    "/admin/devices": "admin-devices.html",
    "/admin/gateways": "admin-gateways.html",
    "/admin/network": "admin-network.html",
    "/admin/facilities": "admin-facilities.html",
    "/admin/routes": "admin-routes.html",
    "/admin/announcements": "admin-announcements.html",
    "/admin/lost-persons": "admin-lost-persons.html",
    "/admin/authorities": "admin-authorities.html",
    "/admin/analytics": "admin-analytics.html",
    "/developer/device-simulator": "developer-simulator.html",
    "/developer/architecture": "architecture.html",
}


def _make_page_handler(filename: str):
    async def _handler():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", filename))

    return _handler


for path, filename in PAGE_ROUTES.items():
    app.add_api_route(path, _make_page_handler(filename), methods=["GET"], include_in_schema=False)
