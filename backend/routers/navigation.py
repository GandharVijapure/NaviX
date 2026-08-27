"""
Simplified navigation guidance between a user and a chosen facility (or any
two points) -- spec section 6/15. See services/navigation_service.py for the
straight-line bearing math and why real road routing isn't attempted yet.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Facility
from ..services.navigation_service import get_directions

router = APIRouter(prefix="/api/navigation", tags=["Navigation"])


@router.get("/directions", response_model=schemas.DirectionsOut)
def directions_between_points(user_lat: float, user_lon: float, dest_lat: float, dest_lon: float, heading: float = 0.0):
    return get_directions(user_lat, user_lon, dest_lat, dest_lon, user_heading=heading)


@router.get("/to-facility/{facility_id}", response_model=schemas.DirectionsOut)
def directions_to_facility(facility_id: int, user_lat: float, user_lon: float, heading: float = 0.0, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return get_directions(user_lat, user_lon, facility.latitude, facility.longitude, user_heading=heading)
