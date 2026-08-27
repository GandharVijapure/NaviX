"""
Volunteer roster, status/location updates, and nearby-volunteer lookup
(used both by the control room and by a volunteer's own dashboard to see
peers nearby).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user, require_admin, require_volunteer
from ..database import get_db
from ..models import User, Volunteer
from ..services.location_service import nearest_items
from ..services.notification_service import notify_volunteer_update

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])


def _get_own_volunteer(db: Session, user: User) -> Volunteer:
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="No volunteer profile linked to this account")
    return volunteer


@router.get("", response_model=list[schemas.VolunteerOut])
def list_volunteers(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Volunteer).all()


@router.get("/nearby", response_model=list[schemas.VolunteerOut])
def nearby_volunteers(lat: float, lon: float, limit: int = 10, db: Session = Depends(get_db)):
    volunteers = db.query(Volunteer).all()
    ranked = nearest_items(lat, lon, volunteers, limit=limit)
    return [v for v, _dist in ranked]


@router.get("/me", response_model=schemas.VolunteerOut)
def my_profile(db: Session = Depends(get_db), user: User = Depends(require_volunteer)):
    return _get_own_volunteer(db, user)


@router.put("/me/status", response_model=schemas.VolunteerOut)
async def update_my_status(
    payload: schemas.VolunteerStatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_volunteer)
):
    volunteer = _get_own_volunteer(db, user)
    volunteer.status = payload.status
    db.commit()
    db.refresh(volunteer)
    await notify_volunteer_update(schemas.VolunteerOut.model_validate(volunteer).model_dump())
    return volunteer


@router.put("/me/location", response_model=schemas.VolunteerOut)
async def update_my_location(
    payload: schemas.VolunteerLocationUpdate, db: Session = Depends(get_db), user: User = Depends(require_volunteer)
):
    from datetime import datetime

    volunteer = _get_own_volunteer(db, user)
    volunteer.latitude = payload.latitude
    volunteer.longitude = payload.longitude
    if payload.battery_level is not None:
        volunteer.battery_level = payload.battery_level
    volunteer.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(volunteer)
    await notify_volunteer_update(schemas.VolunteerOut.model_validate(volunteer).model_dump())
    return volunteer


@router.put("/{volunteer_id}/status", response_model=schemas.VolunteerOut)
async def admin_update_status(
    volunteer_id: int, payload: schemas.VolunteerStatusUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    volunteer.status = payload.status
    db.commit()
    db.refresh(volunteer)
    await notify_volunteer_update(schemas.VolunteerOut.model_validate(volunteer).model_dump())
    return volunteer
