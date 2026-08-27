"""
Hardware/LoRa gateway-facing API (spec section 11). These endpoints are what
a real ESP32 + SX1278 base station will eventually POST to; for this MVP
they're driven either by the Hardware Simulator page or by backend/simulator.py.
No auth is required on these -- field devices authenticate implicitly via a
known device_id (a real deployment would add a per-device shared secret/HMAC
here without changing the payload shape).
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Device, DeviceStatus, Emergency, EmergencyStatus, Volunteer
from ..services.notification_service import notify_device_update, notify_sos_created, notify_volunteer_update

router = APIRouter(prefix="/api/device", tags=["Devices"])


def _get_or_create_device(db: Session, device_id: str) -> Device:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        device = Device(device_id=device_id, status=DeviceStatus.online)
        db.add(device)
        db.flush()
    return device


@router.post("/location", response_model=schemas.DeviceOut)
async def report_location(payload: schemas.DeviceLocationIn, db: Session = Depends(get_db)):
    device = _get_or_create_device(db, payload.device_id)
    device.latitude = payload.latitude
    device.longitude = payload.longitude
    if payload.battery is not None:
        device.battery = payload.battery
    device.status = DeviceStatus.online
    device.last_seen = payload.timestamp or datetime.utcnow()
    db.commit()
    db.refresh(device)

    # If this device belongs to a volunteer, mirror the location onto their
    # row too so the control-room map and volunteer dashboard stay in sync.
    volunteer = db.query(Volunteer).filter(Volunteer.device_id == payload.device_id).first()
    if volunteer:
        volunteer.latitude = payload.latitude
        volunteer.longitude = payload.longitude
        volunteer.last_seen = device.last_seen
        if payload.battery is not None:
            volunteer.battery_level = payload.battery
        db.commit()
        db.refresh(volunteer)
        await notify_volunteer_update(schemas.VolunteerOut.model_validate(volunteer).model_dump())

    await notify_device_update(schemas.DeviceOut.model_validate(device).model_dump())
    return device


@router.post("/sos", response_model=schemas.EmergencyOut, status_code=201)
async def device_sos(payload: schemas.DeviceSOSIn, db: Session = Depends(get_db)):
    """A field device (button press on an ESP32 unit) raises an SOS on
    behalf of whoever is carrying it -- same emergency pipeline as the
    pilgrim-facing /api/emergencies endpoint."""
    emergency = Emergency(
        type=payload.emergency_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description or f"SOS raised from device {payload.device_id}",
        status=EmergencyStatus.new,
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)
    await notify_sos_created(schemas.EmergencyOut.model_validate(emergency).model_dump())
    return emergency


@router.post("/status", response_model=schemas.DeviceOut)
async def device_status(payload: schemas.DeviceStatusIn, db: Session = Depends(get_db)):
    device = _get_or_create_device(db, payload.device_id)
    device.status = payload.status
    if payload.battery is not None:
        device.battery = payload.battery
    device.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(device)
    await notify_device_update(schemas.DeviceOut.model_validate(device).model_dump())
    return device


@router.post("/heartbeat", response_model=schemas.DeviceOut)
async def device_heartbeat(payload: schemas.DeviceHeartbeatIn, db: Session = Depends(get_db)):
    device = _get_or_create_device(db, payload.device_id)
    device.status = DeviceStatus.online
    device.last_seen = datetime.utcnow()
    if payload.battery is not None:
        device.battery = payload.battery
    if payload.latitude is not None and payload.longitude is not None:
        device.latitude = payload.latitude
        device.longitude = payload.longitude
    db.commit()
    db.refresh(device)
    await notify_device_update(schemas.DeviceOut.model_validate(device).model_dump())
    return device


@router.get("/commands", response_model=list[schemas.DeviceCommandOut])
def get_commands(device_id: str):
    """Placeholder command queue a real device would poll over LoRa/BLE
    (e.g. "update firmware", "change zone", "buzz alert"). No commands are
    queued yet in this MVP -- always returns an empty list."""
    return []


@router.get("", response_model=list[schemas.DeviceOut], tags=["Devices"])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()
