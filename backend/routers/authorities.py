"""
Authority directory (Police, Medical, Crowd Management, Disaster
Management, Missing Person Coordination, ...) -- spec section 32. Reads are
public (an operator/volunteer dashboard can show "who owns this"); writes
are admin-only. No real government API integration -- this only records who
an emergency was routed to (spec section 33).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Authority, User

router = APIRouter(prefix="/api/authorities", tags=["Authorities"])


@router.get("", response_model=list[schemas.AuthorityOut])
def list_authorities(db: Session = Depends(get_db)):
    return db.query(Authority).order_by(Authority.name).all()


@router.get("/{authority_id}", response_model=schemas.AuthorityOut)
def get_authority(authority_id: int, db: Session = Depends(get_db)):
    authority = db.query(Authority).filter(Authority.id == authority_id).first()
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    return authority


@router.post("", response_model=schemas.AuthorityOut, status_code=201)
def create_authority(payload: schemas.AuthorityCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    authority = Authority(**payload.model_dump())
    db.add(authority)
    db.commit()
    db.refresh(authority)
    return authority


@router.put("/{authority_id}", response_model=schemas.AuthorityOut)
def update_authority(
    authority_id: int, payload: schemas.AuthorityUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    authority = db.query(Authority).filter(Authority.id == authority_id).first()
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(authority, field, value)
    db.commit()
    db.refresh(authority)
    return authority


@router.delete("/{authority_id}", status_code=204)
def delete_authority(authority_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    authority = db.query(Authority).filter(Authority.id == authority_id).first()
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    db.delete(authority)
    db.commit()
