"""
Hardware/LoRa gateway-facing API (spec section 11). These endpoints are what
a real ESP32 + SX1278 base station will eventually POST to; for this MVP
they're driven either by the Hardware Simulator page or by backend/simulator.py.
No auth is required on these -- field devices authenticate implicitly via a
known device_id (a real deployment would add a per-device shared secret/HMAC
here without changing the payload shape). Preserved unchanged in shape for
backward compatibility -- see routers/gateways.py for the newer,
API-key-protected, multi-hop-aware ingestion path.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..config import DEVICE_STALE_SECONDS
from ..database import get_db
from ..models import Device, DeviceStatus, EmergencySource, Volunteer
from ..services.emergency_service import create_emergency
from ..services.notification_service import notify_device_updated, notify_volunteer_updated

router = APIRouter(prefix="/api/device", tags=["Devices"])


def _get_or_create_device(db: Session, device_id: str) -> Device:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        device = Device(device_id=device_id, status=DeviceStatus.online)
        db.add(device)
        db.flush()
    return device


def _device_out(device: Device) -> schemas.DeviceOut:
    out = schemas.DeviceOut.model_validate(device)
    out.is_stale = (datetime.utcnow() - device.last_seen) > timedelta(seconds=DEVICE_STALE_SECONDS)
    return out


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
        await notify_volunteer_updated(schemas.VolunteerOut.model_validate(volunteer).model_dump())

    await notify_device_updated(_device_out(device).model_dump())
    return _device_out(device)


@router.post("/sos", response_model=schemas.EmergencyOut, status_code=201)
async def device_sos(payload: schemas.DeviceSOSIn, db: Session = Depends(get_db)):
    """A field device (button press on an ESP32 unit) raises an SOS on
    behalf of whoever is carrying it -- same shared emergency pipeline as
    the pilgrim-facing /api/emergencies endpoint."""
    emergency, _created = await create_emergency(
        db,
        type=payload.emergency_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description or f"SOS raised from device {payload.device_id}",
        source=EmergencySource.volunteer_device,
        device_id=payload.device_id,
        client_request_id=payload.client_request_id,
    )
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
    await notify_device_updated(_device_out(device).model_dump())
    return _device_out(device)


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
    if payload.firmware_version:
        device.firmware_version = payload.firmware_version
    db.commit()
    db.refresh(device)
    await notify_device_updated(_device_out(device).model_dump())
    return _device_out(device)


@router.get("/commands", response_model=list[schemas.DeviceCommandOut])
def get_commands(device_id: str):
    """Placeholder command queue a real device would poll over LoRa/BLE
    (e.g. "update firmware", "change zone", "buzz alert"). No commands are
    queued yet in this MVP -- always returns an empty list."""
    return []


@router.get("", response_model=list[schemas.DeviceOut], tags=["Devices"])
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    stale_ids = []
    for d in devices:
        if (datetime.utcnow() - d.last_seen) > timedelta(seconds=DEVICE_STALE_SECONDS) and d.status == DeviceStatus.online:
            d.status = DeviceStatus.offline
            stale_ids.append(d.id)
    if stale_ids:
        db.commit()
    return [_device_out(d) for d in devices]
