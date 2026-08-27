"""
Thin helpers that routers/simulator call to push a WebSocket event after a
DB write. Centralised here so the event-name vocabulary lives in one place
instead of being scattered (and drifting) across every router.
"""
from ..websocket_manager import manager


async def notify_sos_created(emergency: dict) -> None:
    await manager.broadcast("sos_created", emergency)


async def notify_emergency_updated(emergency: dict) -> None:
    await manager.broadcast("emergency_updated", emergency)


async def notify_volunteer_update(volunteer: dict) -> None:
    await manager.broadcast("volunteer_update", volunteer)


async def notify_device_update(device: dict) -> None:
    await manager.broadcast("device_update", device)


async def notify_announcement(announcement: dict) -> None:
    await manager.broadcast("announcement", announcement)


async def notify_facility_update(facility: dict) -> None:
    await manager.broadcast("facility_update", facility)


async def notify_lost_person_update(lost_person: dict) -> None:
    await manager.broadcast("lost_person_update", lost_person)
