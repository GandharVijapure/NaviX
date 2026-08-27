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
    AuthorityType,
    DeviceStatus,
    DeviceType,
    DispatchStatus,
    EmergencyPriority,
    EmergencySource,
    EmergencyStatus,
    EmergencyType,
    FacilityStatus,
    FacilityType,
    GatewayStatus,
    LostPersonStatus,
    NodeRole,
    UserRole,
    VolunteerStatus,
)

# Reusable field constraints (spec section 78) -------------------------------
Latitude = Field(ge=-90, le=90)
Longitude = Field(ge=-180, le=180)
BatteryPct = Field(ge=0, le=100)


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
    latitude: float = Latitude
    longitude: float = Longitude
    battery: Optional[int] = BatteryPct
    timestamp: Optional[datetime] = None


class DeviceSOSIn(BaseModel):
    device_id: str
    latitude: float = Latitude
    longitude: float = Longitude
    emergency_type: EmergencyType = EmergencyType.other
    description: Optional[str] = Field(default=None, max_length=2000)
    client_request_id: Optional[str] = Field(default=None, max_length=64)


class DeviceStatusIn(BaseModel):
    device_id: str
    status: DeviceStatus
    battery: Optional[int] = BatteryPct


class DeviceHeartbeatIn(BaseModel):
    device_id: str
    battery: Optional[int] = BatteryPct
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    firmware_version: Optional[str] = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: str
    volunteer_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery: int
    status: DeviceStatus
    device_type: DeviceType
    node_role: NodeRole
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    gateway_id: Optional[int] = None
    last_rssi: Optional[int] = None
    last_snr: Optional[float] = None
    last_seen: datetime
    is_stale: bool = False


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
    latitude: float = Latitude
    longitude: float = Longitude
    description: Optional[str] = Field(default=None, max_length=2000)
    reporter_contact: Optional[str] = Field(default=None, max_length=64)
    accuracy: Optional[float] = None
    # Idempotency key (spec section 47): a client generates this once and
    # resends the same value on retry after an offline period. The server
    # returns the original emergency instead of creating a duplicate.
    client_request_id: Optional[str] = Field(default=None, max_length=64)


class EmergencyUpdate(BaseModel):
    status: Optional[EmergencyStatus] = None
    assigned_volunteer: Optional[int] = None
    assigned_authority: Optional[int] = None
    priority: Optional[EmergencyPriority] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class EmergencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: EmergencyType
    latitude: float
    longitude: float
    description: Optional[str] = None
    status: EmergencyStatus
    assigned_volunteer: Optional[int] = None
    assigned_authority: Optional[int] = None
    reporter_contact: Optional[str] = None
    source: EmergencySource
    priority: EmergencyPriority
    client_request_id: Optional[str] = None
    accuracy: Optional[float] = None
    origin_node: Optional[str] = None
    gateway_node: Optional[str] = None
    hop_count: Optional[int] = None
    rssi: Optional[int] = None
    snr: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class EmergencyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    emergency_id: int
    event_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime


class NearestVolunteerOut(BaseModel):
    volunteer_id: int
    name: str
    distance_km: float
    status: VolunteerStatus


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
    # Targeted-announcement architecture (spec section 38) -- "all" is the
    # only wired-up value for now; route/zone targeting is a future UI.
    target_type: str = "all"


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
    target_type: str = "all"


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
    client_request_id: Optional[str] = None
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


# ---------------------------------------------------------------------------
# Gateways / LoRa mesh ingestion (spec sections 18-23)
# ---------------------------------------------------------------------------

class GatewayHeartbeatIn(BaseModel):
    gateway_id: str
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery: Optional[int] = BatteryPct
    internet_status: Optional[str] = None
    bluetooth_status: Optional[str] = None


class GatewayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gateway_id: str
    name: Optional[str] = None
    volunteer_id: Optional[int] = None
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: GatewayStatus
    internet_status: str
    bluetooth_status: str
    battery: Optional[int] = None
    messages_received: int
    last_seen: datetime
    is_stale: bool = False


class GatewayMessagePayload(BaseModel):
    """Decoded application-layer content of one LoRa message. Shape depends
    on message_type -- SOS messages carry emergency_type/lat/lon/description,
    LOCATION/HEARTBEAT messages carry just position/battery."""
    emergency_type: Optional[EmergencyType] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    battery: Optional[int] = None
    timestamp: Optional[datetime] = None


class GatewayMessageIn(BaseModel):
    gateway_id: str
    message_id: str = Field(max_length=128)
    message_type: str = Field(default="SOS", max_length=32)
    origin_node: Optional[str] = None
    previous_hop: Optional[str] = None
    hop_count: int = 0
    ttl: Optional[int] = None
    rssi: Optional[int] = None
    snr: Optional[float] = None
    payload: GatewayMessagePayload


class GatewayMessageAck(BaseModel):
    accepted: bool
    duplicate: bool
    message_id: str
    emergency_id: Optional[int] = None


class LoRaMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    message_id: str
    message_type: str
    origin_node: Optional[str] = None
    previous_hop: Optional[str] = None
    gateway_node: Optional[str] = None
    hop_count: int
    rssi: Optional[int] = None
    snr: Optional[float] = None
    emergency_id: Optional[int] = None
    received_at: datetime
    processed: bool


# ---------------------------------------------------------------------------
# Authorities / dispatch (spec sections 32-35)
# ---------------------------------------------------------------------------

class AuthorityCreate(BaseModel):
    name: str
    type: AuthorityType
    contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    active: bool = True


class AuthorityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AuthorityType] = None
    contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class AuthorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: AuthorityType
    contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    active: bool
    notes: Optional[str] = None
    created_at: datetime


class DispatchCreate(BaseModel):
    emergency_id: int
    authority_id: int
    notes: Optional[str] = None


class DispatchUpdate(BaseModel):
    status: Optional[DispatchStatus] = None
    notes: Optional[str] = None


class DispatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    emergency_id: int
    authority_id: int
    status: DispatchStatus
    notes: Optional[str] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    responding_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Pre-stored routes (spec sections 10-12)
# ---------------------------------------------------------------------------

class RouteWaypointIn(BaseModel):
    sequence: int
    latitude: float = Latitude
    longitude: float = Longitude
    instruction: Optional[str] = None
    landmark: Optional[str] = None


class RouteWaypointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sequence: int
    latitude: float
    longitude: float
    instruction: Optional[str] = None
    landmark: Optional[str] = None


class RouteCreate(BaseModel):
    name: str
    source_label: Optional[str] = None
    destination_label: Optional[str] = None
    waypoints: list[RouteWaypointIn] = Field(default_factory=list)


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    source_label: Optional[str] = None
    destination_label: Optional[str] = None
    active: Optional[bool] = None
    waypoints: Optional[list[RouteWaypointIn]] = None


class RouteSummaryOut(BaseModel):
    """Lightweight version-check payload -- lets the PWA compare
    local vs server route version without downloading all waypoints."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    version: int
    active: bool
    updated_at: datetime
    waypoint_count: int = 0


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    version: int
    source_label: Optional[str] = None
    destination_label: Optional[str] = None
    total_distance_km: Optional[float] = None
    active: bool
    updated_at: datetime
    waypoints: list[RouteWaypointOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

class HealthOut(BaseModel):
    status: str
    database: str
    websocket_connections: int
    simulation_running: bool
    version: str
