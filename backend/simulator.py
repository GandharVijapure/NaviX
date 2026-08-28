"""
Demo-mode simulator (spec sections 10/24). Stands in for the real
ESP32+LoRa mesh: every tick it nudges each volunteer's GPS position a
little, refreshes device heartbeats/battery, and occasionally raises a
random demo emergency -- broadcasting every change over the same WebSocket
channel real hardware updates would use, so the control-room dashboard
updates identically either way.

Started/stopped via POST /api/admin/simulation/start|stop (see main.py).

DISABLED (operator decision): the control room is meant to reflect only
real submissions now, not auto-generated demo noise. `start()` is a
permanent no-op below -- flip DISABLED back to False to re-enable it for a
future demo session.
"""
import asyncio
import logging
import random
from datetime import datetime

from sqlalchemy.orm import Session

from . import schemas
from .database import SessionLocal
from .models import Device, DeviceStatus, Emergency, EmergencySource, EmergencyStatus, EmergencyType, Gateway, GatewayStatus, Volunteer
from .services.notification_service import notify_device_updated, notify_gateway_updated, notify_sos_created, notify_volunteer_updated

logger = logging.getLogger("navix.simulator")

TICK_SECONDS = 3
STEP_DEGREES = 0.0006  # small GPS jitter per tick, keeps movement visible but local
RANDOM_EMERGENCY_CHANCE = 0.04  # per volunteer, per tick
# Safety cap: without this, a long-running demo session accumulates simulated
# emergencies forever (nothing auto-resolves them), eventually burying the
# dashboard's Active SOS count under thousands of fake entries. Once this many
# simulator-sourced emergencies are still unresolved, the tick stops minting
# new ones until an operator resolves some (or real submissions come in).
MAX_ACTIVE_SIMULATED_EMERGENCIES = 15

DISABLED = True  # see module docstring

_task: asyncio.Task | None = None
_running = False


def is_running() -> bool:
    return _running


async def _tick(db: Session) -> None:
    volunteers = db.query(Volunteer).filter(Volunteer.status != "offline").all()
    active_simulated = db.query(Emergency).filter(
        Emergency.source == EmergencySource.simulator,
        Emergency.status != EmergencyStatus.resolved,
    ).count()
    for volunteer in volunteers:
        volunteer.latitude = round(volunteer.latitude + random.uniform(-STEP_DEGREES, STEP_DEGREES), 6)
        volunteer.longitude = round(volunteer.longitude + random.uniform(-STEP_DEGREES, STEP_DEGREES), 6)
        volunteer.battery_level = max(5, min(100, volunteer.battery_level + random.randint(-1, 1)))
        volunteer.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(volunteer)
        await notify_volunteer_updated(schemas.VolunteerOut.model_validate(volunteer).model_dump())

        if volunteer.device_id:
            device = db.query(Device).filter(Device.device_id == volunteer.device_id).first()
            if device:
                device.latitude = volunteer.latitude
                device.longitude = volunteer.longitude
                device.battery = volunteer.battery_level
                device.status = DeviceStatus.online
                device.last_seen = datetime.utcnow()
                # Bounded, realistic-looking RSSI/SNR jitter (spec section
                # 58) -- purely cosmetic telemetry for the field-network
                # demo view, not derived from any real radio.
                device.last_rssi = max(-120, min(-40, (device.last_rssi or -85) + random.randint(-3, 3)))
                device.last_snr = round(max(-5.0, min(15.0, (device.last_snr or 6.0) + random.uniform(-0.5, 0.5))), 1)
                db.commit()
                db.refresh(device)
                await notify_device_updated(schemas.DeviceOut.model_validate(device).model_dump())

        if active_simulated < MAX_ACTIVE_SIMULATED_EMERGENCIES and random.random() < RANDOM_EMERGENCY_CHANCE:
            emergency = Emergency(
                type=random.choice(list(EmergencyType)),
                latitude=volunteer.latitude,
                longitude=volunteer.longitude,
                description=f"Simulated demo emergency near volunteer {volunteer.name}",
                status=EmergencyStatus.new,
                source=EmergencySource.simulator,
                device_id=volunteer.device_id,
            )
            db.add(emergency)
            db.commit()
            db.refresh(emergency)
            active_simulated += 1
            await notify_sos_created(schemas.EmergencyOut.model_validate(emergency).model_dump())

    # Gateway heartbeat -- keeps GW-01 (seeded) looking alive while demo
    # mode runs, with slightly jittered battery, matching the volunteer loop.
    gateways = db.query(Gateway).all()
    for gateway in gateways:
        gateway.status = GatewayStatus.online
        gateway.last_seen = datetime.utcnow()
        if gateway.battery is not None:
            gateway.battery = max(5, min(100, gateway.battery + random.randint(-1, 1)))
        db.commit()
        db.refresh(gateway)
        await notify_gateway_updated(schemas.GatewayOut.model_validate(gateway).model_dump())


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
    """Returns True if it was (re)started, False if already running or disabled."""
    global _task
    if DISABLED:
        logger.info("Simulator start requested but simulator is disabled -- ignoring")
        return False
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
