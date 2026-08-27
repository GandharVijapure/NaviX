"""
Pydantic schemas used for request validation and response serialization.

Naming convention: `<Thing>Create` for POST bodies, `<Thing>Update` for
PATCH bodies (all-optional), `<Thing>Out` for responses.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    AnnouncementCategory,
    AnnouncementPriority,
    DeviceStatus,
    EmergencyStatus,
    EmergencyType,
    FacilityStatus,
    FacilityType,
    LostPersonStatus,
    UserRole,
    VolunteerStatus,
)


# ---------------------------------------------------------------------------
# Auth / Users
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.volunteer
    # volunteer-only extras, used to also create the linked Volunteer row
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    assigned_zone: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    name: str
    role: UserRole
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Volunteers
# ---------------------------------------------------------------------------

class VolunteerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    name: str
    phone: Optional[str] = None
    device_id: Optional[str] = None
    latitude: float
    longitude: float
    status: VolunteerStatus
    assigned_zone: Optional[str] = None
    battery_level: int
    last_seen: datetime


class VolunteerStatusUpdate(BaseModel):
    status: VolunteerStatus


class VolunteerLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    battery_level: Optional[int] = None


# ---------------------------------------------------------------------------
# Devices (ESP32 / LoRa gateway facing)
# ---------------------------------------------------------------------------

class DeviceLocationIn(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    battery: Optional[int] = None
    timestamp: Optional[datetime] = None


class DeviceSOSIn(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    emergency_type: EmergencyType = EmergencyType.other
    description: Optional[str] = None


class DeviceStatusIn(BaseModel):
    device_id: str
    status: DeviceStatus
    battery: Optional[int] = None


class DeviceHeartbeatIn(BaseModel):
    device_id: str
    battery: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: str
    volunteer_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery: int
    status: DeviceStatus
    last_seen: datetime


class DeviceCommandOut(BaseModel):
    device_id: str
    command: str
    payload: Optional[dict] = None


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------

class FacilityCreate(BaseModel):
    name: str
    type: FacilityType
    latitude: float
    longitude: float
    description: Optional[str] = None
    status: FacilityStatus = FacilityStatus.open
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    contact: Optional[str] = None


class FacilityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[FacilityType] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    status: Optional[FacilityStatus] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    contact: Optional[str] = None


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: FacilityType
    latitude: float
    longitude: float
    description: Optional[str] = None
    status: FacilityStatus
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    contact: Optional[str] = None


class FacilityNearbyOut(FacilityOut):
    distance_km: float


# ---------------------------------------------------------------------------
# Emergencies / SOS
# ---------------------------------------------------------------------------

class EmergencyCreate(BaseModel):
    type: EmergencyType
    latitude: float
    longitude: float
    description: Optional[str] = None
    reporter_contact: Optional[str] = None


class EmergencyUpdate(BaseModel):
    status: Optional[EmergencyStatus] = None
    assigned_volunteer: Optional[int] = None


class EmergencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: EmergencyType
    latitude: float
    longitude: float
    description: Optional[str] = None
    status: EmergencyStatus
    assigned_volunteer: Optional[int] = None
    reporter_contact: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    category: AnnouncementCategory = AnnouncementCategory.general
    priority: AnnouncementPriority = AnnouncementPriority.normal
    created_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    category: Optional[AnnouncementCategory] = None
    priority: Optional[AnnouncementPriority] = None
    expires_at: Optional[datetime] = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    message: str
    category: AnnouncementCategory
    priority: AnnouncementPriority
    created_by: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Lost persons
# ---------------------------------------------------------------------------

class LostPersonUpdate(BaseModel):
    status: LostPersonStatus


class LostPersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    photo: Optional[str] = None
    description: Optional[str] = None
    clothing_description: Optional[str] = None
    last_seen_location: Optional[str] = None
    last_seen_latitude: Optional[float] = None
    last_seen_longitude: Optional[float] = None
    last_seen_time: Optional[datetime] = None
    contact: Optional[str] = None
    status: LostPersonStatus
    created_at: datetime


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

class DirectionsOut(BaseModel):
    distance_m: float
    distance_km: float
    bearing_deg: float
    compass_direction: str
    turn_hint: str
    estimated_walk_minutes: float
