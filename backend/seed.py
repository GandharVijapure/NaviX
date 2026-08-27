"""
Idempotent demo-data generator (spec section 23). Runs once at startup
(see main.py) only if the `users` table is empty, so re-running the server
never duplicates data. All coordinates are fictional but clustered around a
Pune-area "Wari route" so every demo marker shows up together on the map.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    Announcement,
    AnnouncementCategory,
    AnnouncementPriority,
    Device,
    DeviceStatus,
    Emergency,
    EmergencyStatus,
    EmergencyType,
    Facility,
    FacilityStatus,
    FacilityType,
    LostPerson,
    LostPersonStatus,
    User,
    UserRole,
    Volunteer,
    VolunteerStatus,
)

# Roughly the Alandi-Pune stretch of the Pandharpur Wari route.
BASE_LAT, BASE_LON = 18.5204, 73.8567


def _jitter(base: float, spread: float = 0.012) -> float:
    return round(base + random.uniform(-spread, spread), 6)


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return  # already seeded

    _seed_users_and_volunteers(db)
    _seed_facilities(db)
    _seed_emergencies(db)
    _seed_announcements(db)
    _seed_lost_persons(db)
    db.commit()


def _seed_users_and_volunteers(db: Session) -> None:
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        name="Control Room Admin",
        role=UserRole.admin,
    )
    db.add(admin)

    volunteer_names = [
        "Ramesh Patil", "Sunita More", "Ganesh Jadhav", "Aarti Kulkarni", "Vikram Shinde",
        "Pooja Deshmukh", "Sandeep Pawar", "Meera Joshi", "Anil Gaikwad", "Kavita Bhosale",
    ]

    first_volunteer_user = User(
        username="volunteer1",
        password_hash=hash_password("volunteer123"),
        name=volunteer_names[0],
        phone="9800000001",
        role=UserRole.volunteer,
    )
    db.add(first_volunteer_user)
    db.flush()

    for i, name in enumerate(volunteer_names):
        device_id = f"NVX-{i + 1:03d}"
        volunteer = Volunteer(
            user_id=first_volunteer_user.id if i == 0 else None,
            name=name,
            phone=f"98000000{i + 1:02d}",
            device_id=device_id,
            latitude=_jitter(BASE_LAT),
            longitude=_jitter(BASE_LON),
            status=random.choice(list(VolunteerStatus)),
            assigned_zone=f"Zone {chr(65 + i % 5)}",
            battery_level=random.randint(55, 100),
            last_seen=datetime.utcnow(),
        )
        db.add(volunteer)
        db.flush()

        device = Device(
            device_id=device_id,
            volunteer_id=volunteer.id,
            latitude=volunteer.latitude,
            longitude=volunteer.longitude,
            battery=volunteer.battery_level,
            status=DeviceStatus.online,
            last_seen=datetime.utcnow(),
        )
        db.add(device)


def _seed_facilities(db: Session) -> None:
    medical = [
        ("Medical Camp A - Alandi Gate", "24x7 first-aid and ambulance stand-by."),
        ("Medical Camp B - Chowk 3", "General physician + basic pharmacy."),
        ("Medical Camp C - Riverside", "Heat-stroke and hydration care unit."),
        ("Medical Camp D - Main Ground", "Emergency stabilisation before ambulance transfer."),
        ("Medical Camp E - Gate 7", "Elderly care and first-aid point."),
    ]
    police = [
        ("Police Post B - Checkpoint 4", "Crowd control and lost-and-found desk."),
        ("Police Post - Main Chowk", "Traffic and route-diversion coordination."),
        ("Police Post - East Gate", "Security screening and reporting desk."),
        ("Police Post - Riverside", "Patrol base for riverside crowd zone."),
    ]
    water_food = [
        ("Water Station C - Chowk 2", FacilityType.water, "Free drinking water, 500 pilgrims/hr capacity."),
        ("Water Station - Gate 5", FacilityType.water, "RO-filtered water point."),
        ("Food Point - Community Kitchen", FacilityType.food, "Free meals, breakfast and dinner."),
        ("Food Point - Gate 2 Langar", FacilityType.food, "Community-run meal service."),
        ("Water Station - Riverside", FacilityType.water, "Water tanker refill point."),
        ("Food Point - Main Ground", FacilityType.food, "Snacks and tea stall, volunteer run."),
    ]
    help_centres = [
        ("Help Centre - Information Desk", FacilityType.help_centre, "General information and announcements desk."),
    ]

    for name, desc in medical:
        db.add(Facility(
            name=name, type=FacilityType.medical, latitude=_jitter(BASE_LAT), longitude=_jitter(BASE_LON),
            description=desc, status=FacilityStatus.open, opening_time="00:00", closing_time="23:59",
            contact="108",
        ))
    for name, desc in police:
        db.add(Facility(
            name=name, type=FacilityType.police, latitude=_jitter(BASE_LAT), longitude=_jitter(BASE_LON),
            description=desc, status=FacilityStatus.open, opening_time="00:00", closing_time="23:59",
            contact="100",
        ))
    for name, ftype, desc in water_food:
        db.add(Facility(
            name=name, type=ftype, latitude=_jitter(BASE_LAT), longitude=_jitter(BASE_LON),
            description=desc, status=FacilityStatus.open, opening_time="05:00", closing_time="22:00",
            contact="1800-000-000",
        ))
    for name, ftype, desc in help_centres:
        db.add(Facility(
            name=name, type=ftype, latitude=_jitter(BASE_LAT), longitude=_jitter(BASE_LON),
            description=desc, status=FacilityStatus.open, opening_time="00:00", closing_time="23:59",
            contact="1800-111-111",
        ))


def _seed_emergencies(db: Session) -> None:
    samples = [
        (EmergencyType.medical, EmergencyStatus.new, "Elderly pilgrim feeling dizzy near Chowk 2."),
        (EmergencyType.police, EmergencyStatus.responding, "Overcrowding reported near Checkpoint 4."),
        (EmergencyType.lost_person, EmergencyStatus.acknowledged, "Child separated from family near Main Ground."),
    ]
    for etype, status, desc in samples:
        db.add(Emergency(
            type=etype, latitude=_jitter(BASE_LAT), longitude=_jitter(BASE_LON),
            description=desc, status=status,
            created_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 20)),
        ))


def _seed_announcements(db: Session) -> None:
    samples = [
        (
            "Route Diversion at Checkpoint 4",
            "Main road near checkpoint 4 is temporarily closed. Use alternative route via Gate B.",
            AnnouncementCategory.route_diversion, AnnouncementPriority.critical,
        ),
        (
            "Free Medical Camps Available",
            "Medical camps A-E are operational 24x7 with free first-aid and ambulance stand-by.",
            AnnouncementCategory.medical, AnnouncementPriority.normal,
        ),
        (
            "Evening Weather Advisory",
            "Light rain expected this evening. Pilgrims are advised to carry rain protection.",
            AnnouncementCategory.weather, AnnouncementPriority.important,
        ),
    ]
    for title, message, category, priority in samples:
        db.add(Announcement(
            title=title, message=message, category=category, priority=priority,
            created_by="Control Room Admin", expires_at=datetime.utcnow() + timedelta(days=2),
        ))


def _seed_lost_persons(db: Session) -> None:
    samples = [
        ("Aaji Kamble", 68, "Female", LostPersonStatus.missing, "Wearing green saree, carrying a cloth bag."),
        ("Omkar Sawant", 9, "Male", LostPersonStatus.possible_match, "Wearing blue school uniform, red cap."),
        ("Yashwant Rao", 74, "Male", LostPersonStatus.found, "White dhoti-kurta, uses a walking stick."),
        ("Sakhu Bai", 55, "Female", LostPersonStatus.reunited, "Yellow saree, orange dupatta."),
    ]
    for name, age, gender, status, clothing in samples:
        db.add(LostPerson(
            name=name, age=age, gender=gender, status=status,
            clothing_description=clothing,
            description="Reported by a fellow pilgrim near the main procession route.",
            last_seen_location="Near Main Ground, Alandi Road",
            last_seen_latitude=_jitter(BASE_LAT), last_seen_longitude=_jitter(BASE_LON),
            last_seen_time=datetime.utcnow() - timedelta(hours=random.randint(1, 6)),
            contact="9800001234",
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 6)),
        ))
