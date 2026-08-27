"""
Dispatch records -- Ground Station -> Authority -> Response Team pipeline
(spec section 35). All admin-only: dispatching is a control-room action.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Dispatch, DispatchStatus, Emergency, EmergencyEvent, User
from ..services.notification_service import notify_dispatch_updated

router = APIRouter(prefix="/api/dispatches", tags=["Dispatches"])


@router.get("", response_model=list[schemas.DispatchOut])
def list_dispatches(emergency_id: int | None = None, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    query = db.query(Dispatch)
    if emergency_id:
        query = query.filter(Dispatch.emergency_id == emergency_id)
    return query.order_by(Dispatch.created_at.desc()).all()


@router.post("", response_model=schemas.DispatchOut, status_code=201)
async def create_dispatch(payload: schemas.DispatchCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    emergency = db.query(Emergency).filter(Emergency.id == payload.emergency_id).first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")

    dispatch = Dispatch(emergency_id=payload.emergency_id, authority_id=payload.authority_id, notes=payload.notes)
    db.add(dispatch)

    emergency.assigned_authority = payload.authority_id
    db.add(EmergencyEvent(
        emergency_id=emergency.id, event_type="authority_assigned",
        old_status=emergency.status.value, new_status=emergency.status.value,
        performed_by=admin.name, notes=f"Dispatched to authority #{payload.authority_id}",
    ))

    db.commit()
    db.refresh(dispatch)
    await notify_dispatch_updated(schemas.DispatchOut.model_validate(dispatch).model_dump())
    return dispatch


@router.put("/{dispatch_id}", response_model=schemas.DispatchOut)
async def update_dispatch(
    dispatch_id: int, payload: schemas.DispatchUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    if payload.status is not None:
        dispatch.status = payload.status
        now = datetime.utcnow()
        if payload.status == DispatchStatus.acknowledged:
            dispatch.acknowledged_at = now
        elif payload.status == DispatchStatus.responding:
            dispatch.responding_at = now
        elif payload.status == DispatchStatus.resolved:
            dispatch.resolved_at = now
    if payload.notes is not None:
        dispatch.notes = payload.notes

    db.commit()
    db.refresh(dispatch)
    await notify_dispatch_updated(schemas.DispatchOut.model_validate(dispatch).model_dump())
    return dispatch
