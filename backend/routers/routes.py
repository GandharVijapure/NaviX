"""
Pre-stored Wari routes for offline waypoint navigation (spec sections 10-12).
Reads are public (the PWA downloads routes to cache in IndexedDB); writes
are admin-only. Every write bumps the route's `version` so clients can
detect staleness with a cheap GET /api/routes (summary) before downloading
the full waypoint list.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Route, RouteWaypoint, User
from ..services.route_service import total_distance_km

router = APIRouter(prefix="/api/routes", tags=["Routes"])


def _replace_waypoints(db: Session, route: Route, waypoints_in: list[schemas.RouteWaypointIn]) -> None:
    db.query(RouteWaypoint).filter(RouteWaypoint.route_id == route.id).delete()
    db.flush()
    for wp in sorted(waypoints_in, key=lambda w: w.sequence):
        db.add(RouteWaypoint(route_id=route.id, **wp.model_dump()))
    db.flush()
    db.refresh(route)
    route.total_distance_km = total_distance_km(route.waypoints)


@router.get("", response_model=list[schemas.RouteSummaryOut])
def list_routes(active_only: bool = True, db: Session = Depends(get_db)):
    """Lightweight version-check list -- the PWA compares this against its
    locally cached route versions before deciding what to (re)download."""
    query = db.query(Route)
    if active_only:
        query = query.filter(Route.active.is_(True))
    routes = query.all()
    return [
        schemas.RouteSummaryOut(
            id=r.id, name=r.name, version=r.version, active=r.active,
            updated_at=r.updated_at, waypoint_count=len(r.waypoints),
        )
        for r in routes
    ]


@router.get("/{route_id}", response_model=schemas.RouteOut)
def get_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/{route_id}/waypoints", response_model=list[schemas.RouteWaypointOut])
def get_route_waypoints(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route.waypoints


@router.get("/{route_id}/download", response_model=schemas.RouteOut)
def download_route(route_id: int, db: Session = Depends(get_db)):
    """Same shape as GET /{id} -- named separately per spec section 12 so
    the PWA's offline-download flow has an explicit, self-documenting URL."""
    return get_route(route_id, db)


@router.post("", response_model=schemas.RouteOut, status_code=201)
def create_route(payload: schemas.RouteCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    route = Route(
        name=payload.name, source_label=payload.source_label, destination_label=payload.destination_label,
        version=1, active=True,
    )
    db.add(route)
    db.flush()
    _replace_waypoints(db, route, payload.waypoints)
    db.commit()
    db.refresh(route)
    return route


@router.put("/{route_id}", response_model=schemas.RouteOut)
def update_route(route_id: int, payload: schemas.RouteUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    data = payload.model_dump(exclude_unset=True, exclude={"waypoints"})
    for field, value in data.items():
        setattr(route, field, value)

    if payload.waypoints is not None:
        _replace_waypoints(db, route, payload.waypoints)

    route.version += 1  # any edit -- metadata or waypoints -- bumps the version clients compare against
    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=204)
def delete_route(route_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    db.delete(route)
    db.commit()
