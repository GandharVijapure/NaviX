"""
Processes decoded LoRa gateway messages (spec sections 18-23). The web
backend never touches raw RF -- it only receives already-decoded JSON from a
gateway (real ESP32 base station, or the developer simulator standing in
for one) and turns it into database rows + WebSocket events.

Duplicate suppression: mesh forwarding can deliver the same message more
than once (multiple relay paths), so every message must carry a
sufficiently-unique `message_id`; this module rejects repeats before doing
any further processing.
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import schemas
from ..models import Device, DeviceStatus, DeviceType, Gateway, GatewayStatus, LoRaMessage, EmergencySource
from .emergency_service import create_emergency
from .notification_service import notify_device_updated, notify_gateway_updated


async def get_or_create_gateway(db: Session, gateway_id: str) -> Gateway:
    gateway = db.query(Gateway).filter(Gateway.gateway_id == gateway_id).first()
    if not gateway:
        gateway = Gateway(gateway_id=gateway_id, status=GatewayStatus.online)
        db.add(gateway)
        db.flush()
    return gateway


async def touch_gateway(db: Session, gateway: Gateway, *, latitude: Optional[float] = None, longitude: Optional[float] = None,
                         battery: Optional[int] = None, internet_status: Optional[str] = None,
                         bluetooth_status: Optional[str] = None, count_message: bool = False) -> None:
    gateway.status = GatewayStatus.online
    gateway.last_seen = datetime.utcnow()
    if latitude is not None and longitude is not None:
        gateway.latitude = latitude
        gateway.longitude = longitude
    if battery is not None:
        gateway.battery = battery
    if internet_status is not None:
        gateway.internet_status = internet_status
    if bluetooth_status is not None:
        gateway.bluetooth_status = bluetooth_status
    if count_message:
        gateway.messages_received = (gateway.messages_received or 0) + 1
    db.commit()
    db.refresh(gateway)
    await notify_gateway_updated(schemas.GatewayOut.model_validate(gateway).model_dump())


async def process_gateway_message(db: Session, payload: schemas.GatewayMessageIn) -> schemas.GatewayMessageAck:
    """Validates the gateway, checks for a duplicate message_id, records the
    LoRaMessage, and (for SOS messages) creates an Emergency. Returns an
    acknowledgement matching spec section 23."""
    gateway = await get_or_create_gateway(db, payload.gateway_id)

    existing = db.query(LoRaMessage).filter(LoRaMessage.message_id == payload.message_id).first()
    if existing:
        await touch_gateway(db, gateway)
        return schemas.GatewayMessageAck(
            accepted=True, duplicate=True, message_id=payload.message_id, emergency_id=existing.emergency_id
        )

    record = LoRaMessage(
        message_id=payload.message_id,
        message_type=payload.message_type,
        origin_node=payload.origin_node,
        previous_hop=payload.previous_hop,
        gateway_node=payload.gateway_id,
        hop_count=payload.hop_count,
        ttl=payload.ttl,
        rssi=payload.rssi,
        snr=payload.snr,
        payload=json.dumps(payload.payload.model_dump(mode="json")),
        processed=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    emergency_id = None
    if payload.message_type.upper() == "SOS" and payload.payload.emergency_type and payload.payload.latitude is not None:
        emergency, _created = await create_emergency(
            db,
            type=payload.payload.emergency_type,
            latitude=payload.payload.latitude,
            longitude=payload.payload.longitude,
            description=payload.payload.description,
            source=EmergencySource.lora_gateway,
            device_id=payload.origin_node,
            origin_node=payload.origin_node,
            gateway_node=payload.gateway_id,
            hop_count=payload.hop_count,
            rssi=payload.rssi,
            snr=payload.snr,
        )
        emergency_id = emergency.id
        record.emergency_id = emergency_id

    # Any node reporting through this gateway is implicitly online -- update
    # its registry entry so admin-network.html reflects live mesh activity.
    if payload.origin_node:
        node = db.query(Device).filter(Device.device_id == payload.origin_node).first()
        if not node:
            node = Device(device_id=payload.origin_node, device_type=DeviceType.volunteer_node)
            db.add(node)
            db.flush()
        node.status = DeviceStatus.online
        node.last_seen = datetime.utcnow()
        node.last_rssi = payload.rssi
        node.last_snr = payload.snr
        if payload.payload.latitude is not None and payload.payload.longitude is not None:
            node.latitude = payload.payload.latitude
            node.longitude = payload.payload.longitude
        if payload.payload.battery is not None:
            node.battery = payload.payload.battery
        db.commit()
        await notify_device_updated(schemas.DeviceOut.model_validate(node).model_dump())

    record.processed = True
    db.commit()

    await touch_gateway(db, gateway, count_message=True)

    return schemas.GatewayMessageAck(accepted=True, duplicate=False, message_id=payload.message_id, emergency_id=emergency_id)
