"""
Single shared function for creating an Emergency, used by every entry point
(public companion app, /api/device/sos, /api/gateway/messages, the
simulator) so priority defaults, idempotency, and WebSocket notification
never drift between call sites (spec section 84).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import schemas
from ..models import DEFAULT_EMERGENCY_PRIORITY, Emergency, EmergencyEvent, EmergencySource, EmergencyStatus, EmergencyType
from .notification_service import notify_emergency_created


async def create_emergency(
    db: Session,
    *,
    type: EmergencyType,
    latitude: float,
    longitude: float,
    description: Optional[str] = None,
    reporter_contact: Optional[str] = None,
    source: EmergencySource = EmergencySource.companion_app,
    accuracy: Optional[float] = None,
    client_request_id: Optional[str] = None,
    device_id: Optional[str] = None,
    origin_node: Optional[str] = None,
    gateway_node: Optional[str] = None,
    hop_count: Optional[int] = None,
    rssi: Optional[int] = None,
    snr: Optional[float] = None,
) -> tuple[Emergency, bool]:
    """Creates an Emergency (or returns the existing one if
    `client_request_id` was already seen -- idempotency for offline-queued
    submissions, spec section 47). Returns (emergency, created)."""
    if client_request_id:
        existing = db.query(Emergency).filter(Emergency.client_request_id == client_request_id).first()
        if existing:
            return existing, False

    priority = DEFAULT_EMERGENCY_PRIORITY.get(type.value if hasattr(type, "value") else type, None)

    emergency = Emergency(
        type=type,
        latitude=latitude,
        longitude=longitude,
        description=description,
        reporter_contact=reporter_contact,
        source=source,
        priority=priority,
        accuracy=accuracy,
        client_request_id=client_request_id,
        device_id=device_id,
        origin_node=origin_node,
        gateway_node=gateway_node,
        hop_count=hop_count,
        rssi=rssi,
        snr=snr,
        status=EmergencyStatus.new,
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    db.add(EmergencyEvent(
        emergency_id=emergency.id,
        event_type="created",
        old_status=None,
        new_status=EmergencyStatus.new.value,
        performed_by=source.value,
        timestamp=datetime.utcnow(),
    ))
    db.commit()

    await notify_emergency_created(schemas.EmergencyOut.model_validate(emergency).model_dump())
    return emergency, True
