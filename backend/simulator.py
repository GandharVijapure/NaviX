"""
Demo-mode simulator (spec sections 10/24). Stands in for the real
ESP32+LoRa mesh: every tick it nudges each volunteer's GPS position a
little, refreshes device heartbeats/battery, and occasionally raises a
random demo emergency -- broadcasting every change over the same WebSocket
channel real hardware updates would use, so the control-room dashboard
updates identically either way.

Started/stopped via POST /api/admin/simulation/start|stop (see main.py).
"""
import asyncio
import logging
import random
from datetime import datetime

from sqlalchemy.orm import Session

from . import schemas
from .database import SessionLocal
from .models import Device, DeviceStatus, Emergency, EmergencyStatus, EmergencyType, Volunteer
from .services.notification_service import notify_device_update, notify_sos_created, notify_volunteer_update

logger = logging.getLogger("navix.simulator")

TICK_SECONDS = 3
STEP_DEGREES = 0.0006  # small GPS jitter per tick, keeps movement visible but local
RANDOM_EMERGENCY_CHANCE = 0.04  # per volunteer, per tick

_task: asyncio.Task | None = None
_running = False


def is_running() -> bool:
    return _running


async def _tick(db: Session) -> None:
    volunteers = db.query(Volunteer).filter(Volunteer.status != "offline").all()
    for volunteer in volunteers:
        volunteer.latitude = round(volunteer.latitude + random.uniform(-STEP_DEGREES, STEP_DEGREES), 6)
        volunteer.longitude = round(volunteer.longitude + random.uniform(-STEP_DEGREES, STEP_DEGREES), 6)
        volunteer.battery_level = max(5, min(100, volunteer.battery_level + random.randint(-1, 1)))
        volunteer.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(volunteer)
        await notify_volunteer_update(schemas.VolunteerOut.model_validate(volunteer).model_dump())

        if volunteer.device_id:
            device = db.query(Device).filter(Device.device_id == volunteer.device_id).first()
            if device:
                device.latitude = volunteer.latitude
                device.longitude = volunteer.longitude
                device.battery = volunteer.battery_level
                device.status = DeviceStatus.online
                device.last_seen = datetime.utcnow()
                db.commit()
                db.refresh(device)
                await notify_device_update(schemas.DeviceOut.model_validate(device).model_dump())

        if random.random() < RANDOM_EMERGENCY_CHANCE:
            emergency = Emergency(
                type=random.choice(list(EmergencyType)),
                latitude=volunteer.latitude,
                longitude=volunteer.longitude,
                description=f"Simulated demo emergency near volunteer {volunteer.name}",
                status=EmergencyStatus.new,
            )
            db.add(emergency)
            db.commit()
            db.refresh(emergency)
            await notify_sos_created(schemas.EmergencyOut.model_validate(emergency).model_dump())


async def _run_loop() -> None:
    global _running
    _running = True
    logger.info("NaviX simulator started")
    try:
        while _running:
            db = SessionLocal()
            try:
                await _tick(db)
            except Exception:
                logger.exception("Simulator tick failed")
            finally:
                db.close()
            await asyncio.sleep(TICK_SECONDS)
    finally:
        _running = False
        logger.info("NaviX simulator stopped")


def start() -> bool:
    """Returns True if it was (re)started, False if already running."""
    global _task
    if _running:
        return False
    _task = asyncio.create_task(_run_loop())
    return True


def stop() -> bool:
    global _running, _task
    if not _running:
        return False
    _running = False
    if _task:
        _task.cancel()
    return True
