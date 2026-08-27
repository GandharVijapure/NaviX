"""
Emergencies / SOS pipeline. POST is public (a pilgrim in trouble should
never be blocked by a login screen); status changes and responder
assignment are control-room/admin actions. Every write broadcasts over
WebSocket so the control-room map + stat cards update live.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Emergency, EmergencyStatus, User, Volunteer
from ..services.location_service import nearest_items
from ..services.notification_service import notify_emergency_updated, notify_sos_created

router = APIRouter(prefix="/api/emergencies", tags=["Emergencies"])


@router.post("", response_model=schemas.EmergencyOut, status_code=201)
async def create_emergency(payload: schemas.EmergencyCreate, db: Session = Depends(get_db)):
    """Public SOS submission -- spec section 8. No auth required."""
    emergency = Emergency(**payload.model_dump(), status=EmergencyStatus.new)
    db.add(emergency)
    db.commit()
    db.refresh(emergency)
    await notify_sos_created(schemas.EmergencyOut.model_validate(emergency).model_dump())
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


@router.get("/{emergency_id}/nearest-volunteer", response_model=Optional[schemas.VolunteerOut])
def nearest_volunteer(emergency_id: int, db: Session = Depends(get_db)):
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    volunteers = db.query(Volunteer).all()
    ranked = nearest_items(emergency.latitude, emergency.longitude, volunteers, limit=1)
    return ranked[0][0] if ranked else None


@router.put("/{emergency_id}", response_model=schemas.EmergencyOut)
async def update_emergency(
    emergency_id: int, payload: schemas.EmergencyUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    """Control-room action: assign a responder and/or move the emergency
    through NEW -> ACKNOWLEDGED -> RESPONDER_ASSIGNED -> RESPONDING -> RESOLVED."""
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")

    data = payload.model_dump(exclude_unset=True)
    if "assigned_volunteer" in data and data["assigned_volunteer"] is not None:
        emergency.assigned_volunteer = data["assigned_volunteer"]
        if emergency.status == EmergencyStatus.new:
            emergency.status = EmergencyStatus.responder_assigned
    if "status" in data and data["status"] is not None:
        emergency.status = data["status"]

    db.commit()
    db.refresh(emergency)
    await notify_emergency_updated(schemas.EmergencyOut.model_validate(emergency).model_dump())
    return emergency
