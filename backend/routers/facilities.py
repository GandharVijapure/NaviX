"""
Facility directory + nearest-facility lookup. Reads are public (pilgrims
need this without logging in); writes require control-room/admin auth.
Anything created here shows up immediately on the public map because the
frontend re-fetches from these same endpoints (and gets a WS push too).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Facility, FacilityType, User
from ..services.location_service import haversine_distance_km
from ..services.notification_service import notify_facility_update

router = APIRouter(prefix="/api/facilities", tags=["Facilities"])


@router.get("", response_model=list[schemas.FacilityOut])
def list_facilities(type: Optional[FacilityType] = None, db: Session = Depends(get_db)):
    query = db.query(Facility)
    if type:
        query = query.filter(Facility.type == type)
    return query.order_by(Facility.name).all()


@router.get("/nearby", response_model=list[schemas.FacilityNearbyOut])
def nearby_facilities(
    lat: float,
    lon: float,
    type: Optional[FacilityType] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Core spec-15 endpoint: Haversine-sorted facilities near (lat, lon)."""
    query = db.query(Facility)
    if type:
        query = query.filter(Facility.type == type)
    facilities = query.all()

    results = []
    for facility in facilities:
        distance = haversine_distance_km(lat, lon, facility.latitude, facility.longitude)
        item = schemas.FacilityNearbyOut(
            **schemas.FacilityOut.model_validate(facility).model_dump(),
            distance_km=round(distance, 3),
        )
        results.append(item)

    results.sort(key=lambda f: f.distance_km)
    return results[:limit]


@router.get("/{facility_id}", response_model=schemas.FacilityOut)
def get_facility(facility_id: int, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@router.post("", response_model=schemas.FacilityOut, status_code=201)
async def create_facility(payload: schemas.FacilityCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    facility = Facility(**payload.model_dump())
    db.add(facility)
    db.commit()
    db.refresh(facility)
    await notify_facility_update(schemas.FacilityOut.model_validate(facility).model_dump())
    return facility


@router.put("/{facility_id}", response_model=schemas.FacilityOut)
async def update_facility(
    facility_id: int, payload: schemas.FacilityUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(facility, field, value)
    db.commit()
    db.refresh(facility)
    await notify_facility_update(schemas.FacilityOut.model_validate(facility).model_dump())
    return facility


@router.delete("/{facility_id}", status_code=204)
async def delete_facility(facility_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    facility_id_value = facility.id
    db.delete(facility)
    db.commit()
    await notify_facility_update({"id": facility_id_value, "deleted": True})
