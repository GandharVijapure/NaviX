"""
Community announcements. Reading the active feed is public; creating/
editing is control-room/admin only. Critical-priority announcements are
what the public frontend pins to the top of the page.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import Announcement, User
from ..services.notification_service import notify_announcement

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


@router.get("/active", response_model=list[schemas.AnnouncementOut])
def active_announcements(db: Session = Depends(get_db)):
    """Public feed: excludes expired announcements, critical/important first."""
    now = datetime.utcnow()
    announcements = (
        db.query(Announcement)
        .filter(or_(Announcement.expires_at.is_(None), Announcement.expires_at > now))
        .order_by(Announcement.created_at.desc())
        .all()
    )
    priority_rank = {"critical": 0, "important": 1, "normal": 2}
    announcements.sort(key=lambda a: priority_rank.get(a.priority.value, 3))
    return announcements


@router.get("", response_model=list[schemas.AnnouncementOut])
def list_all_announcements(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Full history (incl. expired) for the control-room management page."""
    return db.query(Announcement).order_by(Announcement.created_at.desc()).all()


@router.post("", response_model=schemas.AnnouncementOut, status_code=201)
async def create_announcement(
    payload: schemas.AnnouncementCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    announcement = Announcement(**payload.model_dump(exclude={"created_by"}), created_by=payload.created_by or admin.name)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    await notify_announcement(schemas.AnnouncementOut.model_validate(announcement).model_dump())
    return announcement


@router.put("/{announcement_id}", response_model=schemas.AnnouncementOut)
async def update_announcement(
    announcement_id: int, payload: schemas.AnnouncementUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(announcement, field, value)
    db.commit()
    db.refresh(announcement)
    await notify_announcement(schemas.AnnouncementOut.model_validate(announcement).model_dump())
    return announcement


@router.delete("/{announcement_id}", status_code=204)
async def delete_announcement(announcement_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    announcement_id_value = announcement.id
    db.delete(announcement)
    db.commit()
    await notify_announcement({"id": announcement_id_value, "deleted": True})
