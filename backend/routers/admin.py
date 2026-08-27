"""
Control-room dashboard stats/analytics + demo-simulation on/off switch.
Not one of the "domain" routers (facilities, emergencies, ...) but a thin
aggregation layer over them, kept separate so main.py stays uncluttered.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, simulator
from ..auth import require_admin
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/admin", tags=["Admin / Analytics"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Top stat cards for the control-room dashboard (spec section 9)."""
    active_sos = db.query(models.Emergency).filter(models.Emergency.status != models.EmergencyStatus.resolved).count()
    volunteers_online = db.query(models.Volunteer).filter(models.Volunteer.status != models.VolunteerStatus.offline).count()
    devices_online = db.query(models.Device).filter(models.Device.status == models.DeviceStatus.online).count()
    medical_cases = db.query(models.Emergency).filter(
        models.Emergency.type == models.EmergencyType.medical,
        models.Emergency.status != models.EmergencyStatus.resolved,
    ).count()
    missing_reports = db.query(models.LostPerson).filter(
        models.LostPerson.status.in_([models.LostPersonStatus.missing, models.LostPersonStatus.possible_match])
    ).count()
    now = datetime.utcnow()
    active_alerts = db.query(models.Announcement).filter(
        (models.Announcement.expires_at.is_(None)) | (models.Announcement.expires_at > now)
    ).count()

    return {
        "active_sos": active_sos,
        "volunteers_online": volunteers_online,
        "devices_online": devices_online,
        "medical_cases": medical_cases,
        "missing_person_reports": missing_reports,
        "active_alerts": active_alerts,
    }


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Lightweight MVP analytics (spec section 25)."""
    emergencies = db.query(models.Emergency).all()

    by_category: dict[str, int] = {}
    resolved = 0
    total_response_minutes = 0.0
    resolved_count_for_avg = 0
    for e in emergencies:
        by_category[e.type.value] = by_category.get(e.type.value, 0) + 1
        if e.status == models.EmergencyStatus.resolved:
            resolved += 1
            delta = (e.updated_at - e.created_at).total_seconds() / 60
            total_response_minutes += delta
            resolved_count_for_avg += 1

    avg_response_minutes = round(total_response_minutes / resolved_count_for_avg, 1) if resolved_count_for_avg else 0

    volunteers = db.query(models.Volunteer).all()
    volunteer_availability: dict[str, int] = {}
    for v in volunteers:
        volunteer_availability[v.status.value] = volunteer_availability.get(v.status.value, 0) + 1

    devices_online = db.query(models.Device).filter(models.Device.status == models.DeviceStatus.online).count()
    devices_offline = db.query(models.Device).filter(models.Device.status == models.DeviceStatus.offline).count()

    facilities = db.query(models.Facility).all()
    facility_distribution: dict[str, int] = {}
    for f in facilities:
        facility_distribution[f.type.value] = facility_distribution.get(f.type.value, 0) + 1

    return {
        "emergencies_by_category": by_category,
        "average_response_minutes": avg_response_minutes,
        "resolved_cases": resolved,
        "total_emergencies": len(emergencies),
        "devices_online": devices_online,
        "devices_offline": devices_offline,
        "volunteer_availability": volunteer_availability,
        "facility_distribution": facility_distribution,
    }


@router.post("/simulation/start")
async def start_simulation():
    """No auth required -- this only drives the demo-mode simulator (fake
    hardware movement), used from both the control room and the developer
    simulator page so it's easy to demo without a login step in the way.
    Must run as `async def` (not sync `def`) so it executes directly on the
    main event loop -- asyncio.create_task() requires a running loop, which
    a sync endpoint (run in FastAPI's worker threadpool) doesn't have."""
    started = simulator.start()
    return {"running": True, "already_running": not started}


@router.post("/simulation/stop")
async def stop_simulation():
    stopped = simulator.stop()
    return {"running": False, "was_running": stopped}


@router.get("/simulation/status")
def simulation_status():
    return {"running": simulator.is_running()}
