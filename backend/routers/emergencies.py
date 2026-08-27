"""
Emergencies / SOS pipeline. POST is public (a pilgrim in trouble should
never be blocked by a login screen); status changes and responder
assignment are control-room/admin actions. Every write broadcasts over
WebSocket so the control-room map + stat cards update live. Emergency
creation itself is delegated to services/emergency_service.py so every
entry point (this router, /api/device/sos, /api/gateway/messages, the
simulator) shares one code path.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Emergency, EmergencyEvent, EmergencySource, EmergencyStatus, User, Volunteer, VolunteerStatus
from ..services.emergency_service import create_emergency
from ..services.location_service import nearest_items
from ..services.notification_service import notify_emergency_updated

router = APIRouter(prefix="/api/emergencies", tags=["Emergencies"])


@router.post("", response_model=schemas.EmergencyOut, status_code=201)
async def create_emergency_endpoint(payload: schemas.EmergencyCreate, response: Response, db: Session = Depends(get_db)):
    """Public SOS submission -- spec section 8. No auth required. Repeating
    the same `client_request_id` (e.g. after an offline retry) returns the
    original emergency instead of creating a duplicate."""
    emergency, created = await create_emergency(
        db,
        type=payload.type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description,
        reporter_contact=payload.reporter_contact,
        accuracy=payload.accuracy,
        client_request_id=payload.client_request_id,
        source=EmergencySource.companion_app,
    )
    response.status_code = 201 if created else 200
    return emergency


@router.get("", response_model=list[schemas.EmergencyOut])
def list_emergencies(status: Optional[EmergencyStatus] = None, db: Session = Depends(get_db)):
    query = db.query(Emergency)
    if status:
        query = query.filter(Emergency.status == status)
    return query.order_by(Emergency.created_at.desc()).all()


@router.get("/{emergency_id}", response_model=schemas.EmergencyOut)
def get_emergency(emergency_id: int, db: Session = Depends(get_db)):
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    return emergency


@router.get("/{emergency_id}/events", response_model=list[schemas.EmergencyEventOut])
def get_emergency_events(emergency_id: int, db: Session = Depends(get_db)):
    """Status/assignment history for the emergency detail view (spec
    sections 15/30/69)."""
    return (
        db.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == emergency_id)
        .order_by(EmergencyEvent.timestamp.asc())
        .all()
    )


@router.get("/{emergency_id}/nearest-volunteer", response_model=Optional[schemas.VolunteerOut])
def nearest_volunteer(emergency_id: int, db: Session = Depends(get_db)):
    """Kept for backward compatibility -- prefer /nearest-volunteers (plural)."""
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    volunteers = db.query(Volunteer).all()
    ranked = nearest_items(emergency.latitude, emergency.longitude, volunteers, limit=1)
    return ranked[0][0] if ranked else None


@router.get("/{emergency_id}/nearest-volunteers", response_model=list[schemas.NearestVolunteerOut])
def nearest_volunteers(emergency_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Multiple candidates, closest first, available volunteers prioritized
    (spec section 31). The ground-station operator picks who to assign --
    this never auto-assigns."""
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    volunteers = db.query(Volunteer).all()
    ranked = nearest_items(emergency.latitude, emergency.longitude, volunteers, limit=None)
    ranked.sort(key=lambda pair: (pair[0].status != VolunteerStatus.available, pair[1]))
    return [
        schemas.NearestVolunteerOut(volunteer_id=v.id, name=v.name, distance_km=round(dist, 3), status=v.status)
        for v, dist in ranked[:limit]
    ]


@router.put("/{emergency_id}", response_model=schemas.EmergencyOut)
async def update_emergency(
    emergency_id: int, payload: schemas.EmergencyUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """Control-room action: assign a responder/authority, change priority,
    and/or move the emergency through
    NEW -> ACKNOWLEDGED -> RESPONDER_ASSIGNED -> RESPONDING -> RESOLVED
    (or CANCELLED/DUPLICATE). Every change is recorded as an EmergencyEvent."""
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")

    data = payload.model_dump(exclude_unset=True)
    old_status = emergency.status.value

    if "assigned_volunteer" in data and data["assigned_volunteer"] is not None:
        emergency.assigned_volunteer = data["assigned_volunteer"]
        if emergency.status == EmergencyStatus.new:
            emergency.status = EmergencyStatus.responder_assigned
        db.add(EmergencyEvent(
            emergency_id=emergency.id, event_type="assignment", old_status=old_status,
            new_status=emergency.status.value, performed_by=admin.name,
            notes=f"Assigned volunteer #{data['assigned_volunteer']}",
        ))

    if "assigned_authority" in data and data["assigned_authority"] is not None:
        emergency.assigned_authority = data["assigned_authority"]

    if "priority" in data and data["priority"] is not None:
        emergency.priority = data["priority"]
        db.add(EmergencyEvent(
            emergency_id=emergency.id, event_type="priority_change", old_status=old_status,
            new_status=emergency.status.value, performed_by=admin.name,
            notes=f"Priority set to {data['priority']}",
        ))

    if "status" in data and data["status"] is not None and data["status"].value != old_status:
        emergency.status = data["status"]
        db.add(EmergencyEvent(
            emergency_id=emergency.id, event_type="status_change", old_status=old_status,
            new_status=emergency.status.value, performed_by=admin.name, notes=data.get("notes"),
        ))

    db.commit()
    db.refresh(emergency)
    await notify_emergency_updated(schemas.EmergencyOut.model_validate(emergency).model_dump())
    return emergency
