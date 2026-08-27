"""
Thin helpers that routers/simulator call to push a WebSocket event after a
DB write. Centralised here so the event-name vocabulary lives in one place
instead of being scattered (and drifting) across every router. Event names
match spec section 43.
"""
from ..websocket_manager import manager


async def notify_emergency_created(emergency: dict) -> None:
    await manager.broadcast("emergency_created", emergency)
    # Back-compat alias -- some older frontend pages still listen for this.
    await manager.broadcast("sos_created", emergency)


async def notify_emergency_updated(emergency: dict) -> None:
    await manager.broadcast("emergency_updated", emergency)


async def notify_volunteer_updated(volunteer: dict) -> None:
    await manager.broadcast("volunteer_updated", volunteer)
    await manager.broadcast("volunteer_update", volunteer)  # back-compat alias


async def notify_device_updated(device: dict) -> None:
    await manager.broadcast("device_updated", device)
    await manager.broadcast("device_update", device)  # back-compat alias


async def notify_gateway_updated(gateway: dict) -> None:
    await manager.broadcast("gateway_updated", gateway)


async def notify_announcement_created(announcement: dict) -> None:
    await manager.broadcast("announcement_created", announcement)
    await manager.broadcast("announcement", announcement)  # back-compat alias


async def notify_announcement_updated(announcement: dict) -> None:
    await manager.broadcast("announcement_updated", announcement)
    await manager.broadcast("announcement", announcement)  # back-compat alias


async def notify_facility_updated(facility: dict) -> None:
    await manager.broadcast("facility_updated", facility)
    await manager.broadcast("facility_update", facility)  # back-compat alias


async def notify_lost_person_created(lost_person: dict) -> None:
    await manager.broadcast("lost_person_created", lost_person)
    await manager.broadcast("lost_person_update", lost_person)  # back-compat alias


async def notify_lost_person_updated(lost_person: dict) -> None:
    await manager.broadcast("lost_person_updated", lost_person)
    await manager.broadcast("lost_person_update", lost_person)  # back-compat alias


async def notify_dispatch_updated(dispatch: dict) -> None:
    await manager.broadcast("dispatch_updated", dispatch)


# --- Back-compat names (existing routers import these) ---------------------
notify_sos_created = notify_emergency_created
notify_volunteer_update = notify_volunteer_updated
notify_device_update = notify_device_updated
notify_announcement = notify_announcement_created
notify_facility_update = notify_facility_updated
notify_lost_person_update = notify_lost_person_updated
