"""
Lost person / family reunification. Reporting is public (a worried pilgrim
should never need to log in); status updates (Missing -> Possible Match ->
Found -> Reunited) are control-room/admin actions. Photo upload is optional
multipart form data, saved under static/uploads and served back as a URL.
"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import LostPerson, LostPersonStatus, User
from ..services.notification_service import notify_lost_person_update

router = APIRouter(prefix="/api/lost-persons", tags=["Lost Persons"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.get("", response_model=list[schemas.LostPersonOut])
def list_lost_persons(
    status: Optional[LostPersonStatus] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(LostPerson)
    if status:
        query = query.filter(LostPerson.status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(LostPerson.name.ilike(like))
    return query.order_by(LostPerson.created_at.desc()).all()


@router.get("/{lost_person_id}", response_model=schemas.LostPersonOut)
def get_lost_person(lost_person_id: int, db: Session = Depends(get_db)):
    person = db.query(LostPerson).filter(LostPerson.id == lost_person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Report not found")
    return person


@router.post("", response_model=schemas.LostPersonOut, status_code=201)
async def report_lost_person(
    name: str = Form(...),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    clothing_description: Optional[str] = Form(None),
    last_seen_location: Optional[str] = Form(None),
    last_seen_latitude: Optional[float] = Form(None),
    last_seen_longitude: Optional[float] = Form(None),
    last_seen_time: Optional[datetime] = Form(None),
    contact: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    photo_path = None
    if photo is not None and photo.filename:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Photo must be a JPEG, PNG, WEBP or GIF image")
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        contents = await photo.read()
        with open(dest, "wb") as f:
            f.write(contents)
        photo_path = f"/static/uploads/{filename}"

    person = LostPerson(
        name=name,
        age=age,
        gender=gender,
        photo=photo_path,
        description=description,
        clothing_description=clothing_description,
        last_seen_location=last_seen_location,
        last_seen_latitude=last_seen_latitude,
        last_seen_longitude=last_seen_longitude,
        last_seen_time=last_seen_time,
        contact=contact,
        status=LostPersonStatus.missing,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    await notify_lost_person_update(schemas.LostPersonOut.model_validate(person).model_dump())
    return person


@router.put("/{lost_person_id}/status", response_model=schemas.LostPersonOut)
async def update_status(
    lost_person_id: int, payload: schemas.LostPersonUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    person = db.query(LostPerson).filter(LostPerson.id == lost_person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Report not found")
    person.status = payload.status
    db.commit()
    db.refresh(person)
    await notify_lost_person_update(schemas.LostPersonOut.model_validate(person).model_dump())
    return person
