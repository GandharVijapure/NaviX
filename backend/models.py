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


class DeviceType(str, enum.Enum):
    volunteer_node = "volunteer_node"
    gateway = "gateway"
    simulator = "simulator"


class NodeRole(str, enum.Enum):
    """Where a device sits in the LoRa mesh -- purely descriptive, doesn't
    affect routing (see services/gateway_service.py for the actual
    application-level multi-hop bookkeeping)."""
    sub_volunteer = "sub_volunteer"
    relay = "relay"
    main_gateway = "main_gateway"


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
    cancelled = "CANCELLED"
    duplicate = "DUPLICATE"


class EmergencySource(str, enum.Enum):
    """Where an SOS actually came from -- lets the control room tell a
    public phone report apart from one relayed over the LoRa mesh."""
    companion_app = "companion_app"
    volunteer_device = "volunteer_device"
    lora_gateway = "lora_gateway"
    control_room = "control_room"
    simulator = "simulator"


class EmergencyPriority(str, enum.Enum):
    critical = "critical"
    high = "high"
    normal = "normal"
    low = "low"


# Rule-based default priority per emergency type (spec section 29 -- no fake
# AI prioritization, just a documented mapping an operator can override).
DEFAULT_EMERGENCY_PRIORITY = {
    "medical": EmergencyPriority.high,
    "crowd": EmergencyPriority.high,
    "police": EmergencyPriority.high,
    "lost_person": EmergencyPriority.normal,
    "other": EmergencyPriority.normal,
}


class GatewayStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class AuthorityType(str, enum.Enum):
    medical = "medical"
    police = "police"
    crowd_management = "crowd_management"
    disaster_management = "disaster_management"
    missing_person = "missing_person"
    other = "other"


class DispatchStatus(str, enum.Enum):
    pending = "pending"
    acknowledged = "acknowledged"
    responding = "responding"
    resolved = "resolved"


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
    volunteer, or act as a standalone/base-station node, or be a gateway."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    battery = Column(Integer, default=100)
    status = Column(SAEnum(DeviceStatus), default=DeviceStatus.offline, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # --- Device registry upgrade (spec section 25) -----------------------
    device_type = Column(SAEnum(DeviceType), default=DeviceType.volunteer_node, nullable=False)
    firmware_version = Column(String(32), nullable=True)
    hardware_version = Column(String(32), nullable=True)
    node_role = Column(SAEnum(NodeRole), default=NodeRole.sub_volunteer, nullable=False)
    gateway_id = Column(Integer, ForeignKey("gateways.id"), nullable=True)
    last_rssi = Column(Integer, nullable=True)  # dBm, e.g. -91
    last_snr = Column(Float, nullable=True)     # dB, e.g. 7.2
    registered_at = Column(DateTime, default=datetime.utcnow)


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

    # --- Upgrade: source/priority/audit/idempotency (spec sections 14/15/29/47) ---
    source = Column(SAEnum(EmergencySource), default=EmergencySource.companion_app, nullable=False)
    priority = Column(SAEnum(EmergencyPriority), default=EmergencyPriority.normal, nullable=False)
    client_request_id = Column(String(64), unique=True, nullable=True, index=True)
    device_id = Column(String(64), nullable=True)
    accuracy = Column(Float, nullable=True)
    assigned_authority = Column(Integer, ForeignKey("authorities.id"), nullable=True)
    # LoRa provenance -- populated only when source == lora_gateway
    origin_node = Column(String(64), nullable=True)
    gateway_node = Column(String(64), nullable=True)
    hop_count = Column(Integer, nullable=True)
    rssi = Column(Integer, nullable=True)
    snr = Column(Float, nullable=True)


class EmergencyEvent(Base):
    """Audit trail of every status/assignment change on an emergency (spec
    section 15/69) -- so the control room can show a real history instead of
    just the latest `updated_at`."""
    __tablename__ = "emergency_events"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # e.g. "status_change", "assignment", "priority_change"
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    performed_by = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


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
    # Targeted-announcement architecture (spec section 38) -- "all" is the
    # only wired-up value today; route/zone targeting is a future extension.
    target_type = Column(String(16), default="all", nullable=False)
    target_zone = Column(String(64), nullable=True)
    target_route = Column(String(64), nullable=True)


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
    client_request_id = Column(String(64), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# LoRa mesh / gateway layer (spec sections 21-26)
# ---------------------------------------------------------------------------

class Gateway(Base):
    """A Main Volunteer / gateway node -- the smartphone+LoRa module bridge
    between the field mesh and the internet (spec section 21/22)."""
    __tablename__ = "gateways"

    id = Column(Integer, primary_key=True, index=True)
    gateway_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    device_id = Column(String(64), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(SAEnum(GatewayStatus), default=GatewayStatus.offline, nullable=False)
    internet_status = Column(String(16), default="unknown")
    bluetooth_status = Column(String(16), default="unknown")
    battery = Column(Integer, nullable=True)
    messages_received = Column(Integer, default=0)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoRaMessage(Base):
    """Log of every decoded gateway message (spec section 20) -- also the
    dedup table: `message_id` is unique so mesh-forwarded duplicates are
    rejected instead of creating repeat emergencies."""
    __tablename__ = "lora_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(128), unique=True, index=True, nullable=False)
    message_type = Column(String(32), nullable=False)  # SOS, LOCATION, HEARTBEAT, STATUS
    origin_node = Column(String(64), nullable=True)
    previous_hop = Column(String(64), nullable=True)
    gateway_node = Column(String(64), nullable=True)
    hop_count = Column(Integer, default=0)
    ttl = Column(Integer, nullable=True)
    rssi = Column(Integer, nullable=True)
    snr = Column(Float, nullable=True)
    payload = Column(Text, nullable=True)  # raw JSON payload, for audit/debugging
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Authorities / dispatch (spec sections 32-35)
# ---------------------------------------------------------------------------

class Authority(Base):
    __tablename__ = "authorities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(SAEnum(AuthorityType), nullable=False)
    contact = Column(String(64), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dispatch(Base):
    """Records that an emergency was routed to a specific authority --
    simulated/recorded dispatch, not a live government API integration
    (spec section 33: no real integration without real credentials)."""
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=False, index=True)
    authority_id = Column(Integer, ForeignKey("authorities.id"), nullable=False)
    status = Column(SAEnum(DispatchStatus), default=DispatchStatus.pending, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    responding_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Pre-stored routes for offline waypoint navigation (spec sections 10-12)
# ---------------------------------------------------------------------------

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    source_label = Column(String(128), nullable=True)
    destination_label = Column(String(128), nullable=True)
    total_distance_km = Column(Float, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    waypoints = relationship("RouteWaypoint", back_populates="route", order_by="RouteWaypoint.sequence", cascade="all, delete-orphan")


class RouteWaypoint(Base):
    __tablename__ = "route_waypoints"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    instruction = Column(String(200), nullable=True)
    landmark = Column(String(128), nullable=True)

    route = relationship("Route", back_populates="waypoints")
