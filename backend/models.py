"""
SQLAlchemy ORM models for NaviX.

Tables mirror the spec: users, volunteers, devices, facilities, emergencies,
announcements, lost_persons. Enums are stored as strings (SQLAlchemy Enum)
so the DB stays human-readable and portable to PostgreSQL later.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    volunteer = "volunteer"
    admin = "admin"


class VolunteerStatus(str, enum.Enum):
    available = "available"
    responding = "responding"
    busy = "busy"
    offline = "offline"


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"


class FacilityType(str, enum.Enum):
    medical = "medical"
    police = "police"
    water = "water"
    food = "food"
    help_centre = "help_centre"
    ambulance = "ambulance"
    toilet = "toilet"


class FacilityStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class EmergencyType(str, enum.Enum):
    medical = "medical"
    police = "police"
    lost_person = "lost_person"
    crowd = "crowd"
    other = "other"


class EmergencyStatus(str, enum.Enum):
    new = "NEW"
    acknowledged = "ACKNOWLEDGED"
    responder_assigned = "RESPONDER_ASSIGNED"
    responding = "RESPONDING"
    resolved = "RESOLVED"


class AnnouncementCategory(str, enum.Enum):
    general = "general"
    route_diversion = "route_diversion"
    medical = "medical"
    weather = "weather"
    emergency = "emergency"
    missing_person = "missing_person"
    facility_update = "facility_update"


class AnnouncementPriority(str, enum.Enum):
    normal = "normal"
    important = "important"
    critical = "critical"


class LostPersonStatus(str, enum.Enum):
    missing = "missing"
    possible_match = "possible_match"
    found = "found"
    reunited = "reunited"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class User(Base):
    """Login accounts for volunteers and control-room/admin staff only.
    Pilgrims never need an account -- their features stay anonymous."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    volunteer = relationship("Volunteer", back_populates="user", uselist=False)


class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=True)
    device_id = Column(String(64), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(SAEnum(VolunteerStatus), default=VolunteerStatus.available, nullable=False)
    assigned_zone = Column(String(64), nullable=True)
    battery_level = Column(Integer, default=100)
    last_seen = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="volunteer")


class Device(Base):
    """A physical (or simulated) ESP32+LoRa+GPS unit. May belong to a
    volunteer, or act as a standalone/base-station node."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    battery = Column(Integer, default=100)
    status = Column(SAEnum(DeviceStatus), default=DeviceStatus.offline, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(SAEnum(FacilityType), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(FacilityStatus), default=FacilityStatus.open, nullable=False)
    opening_time = Column(String(16), nullable=True)
    closing_time = Column(String(16), nullable=True)
    contact = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Emergency(Base):
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SAEnum(EmergencyType), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(EmergencyStatus), default=EmergencyStatus.new, nullable=False)
    assigned_volunteer = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    reporter_contact = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(SAEnum(AnnouncementCategory), default=AnnouncementCategory.general, nullable=False)
    priority = Column(SAEnum(AnnouncementPriority), default=AnnouncementPriority.normal, nullable=False)
    created_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class LostPerson(Base):
    __tablename__ = "lost_persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(16), nullable=True)
    photo = Column(String(255), nullable=True)  # relative path under /static/uploads
    description = Column(Text, nullable=True)
    clothing_description = Column(Text, nullable=True)
    last_seen_location = Column(String(200), nullable=True)
    last_seen_latitude = Column(Float, nullable=True)
    last_seen_longitude = Column(Float, nullable=True)
    last_seen_time = Column(DateTime, nullable=True)
    contact = Column(String(64), nullable=True)
    status = Column(SAEnum(LostPersonStatus), default=LostPersonStatus.missing, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
