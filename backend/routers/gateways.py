"""
Gateway management + LoRa message ingestion (spec sections 21-23). This is
the production-style entry point real ESP32/LoRa base stations will POST
decoded mesh messages to; today it's driven by the developer simulator.

`POST /api/gateway/messages` requires a shared gateway API key (spec
section 49) since -- unlike the pilgrim-facing endpoints -- this is meant to
be called by trusted field hardware, not arbitrary browsers.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin, require_gateway_key
from ..config import DEVICE_STALE_SECONDS
from ..database import get_db
from ..models import Gateway, GatewayStatus, LoRaMessage, User
from ..services.gateway_service import get_or_create_gateway, process_gateway_message, touch_gateway

router = APIRouter(prefix="/api/gateways", tags=["Gateways"])
message_router = APIRouter(prefix="/api/gateway", tags=["Gateways"])


def _with_staleness(gateway: Gateway) -> schemas.GatewayOut:
    out = schemas.GatewayOut.model_validate(gateway)
    stale = (datetime.utcnow() - gateway.last_seen) > timedelta(seconds=DEVICE_STALE_SECONDS)
    out.is_stale = stale
    if stale:
        out.status = GatewayStatus.offline
    return out


@router.get("", response_model=list[schemas.GatewayOut])
def list_gateways(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return [_with_staleness(g) for g in db.query(Gateway).all()]


@router.get("/{gateway_id}", response_model=schemas.GatewayOut)
def get_gateway(gateway_id: str, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    gateway = db.query(Gateway).filter(Gateway.gateway_id == gateway_id).first()
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return _with_staleness(gateway)


@message_router.post("/heartbeat", response_model=schemas.GatewayOut)
async def gateway_heartbeat(payload: schemas.GatewayHeartbeatIn, db: Session = Depends(get_db), _key=Depends(require_gateway_key)):
    gateway = await get_or_create_gateway(db, payload.gateway_id)
    if payload.name:
        gateway.name = payload.name
    await touch_gateway(
        db, gateway,
        latitude=payload.latitude, longitude=payload.longitude, battery=payload.battery,
        internet_status=payload.internet_status, bluetooth_status=payload.bluetooth_status,
    )
    return gateway


@router.get("/messages/recent", response_model=list[schemas.LoRaMessageOut])
def recent_messages(limit: int = 50, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Recent decoded LoRa messages -- feeds the Field Network Status page
    (spec section 55) so an operator can see per-node hop-count/RSSI/SNR
    history, not just current position."""
    return db.query(LoRaMessage).order_by(LoRaMessage.received_at.desc()).limit(limit).all()


@message_router.post("/messages", response_model=schemas.GatewayMessageAck)
async def gateway_messages(payload: schemas.GatewayMessageIn, db: Session = Depends(get_db), _key=Depends(require_gateway_key)):
    """Production-style decoded-LoRa-message ingestion endpoint (spec
    section 23). Validates the gateway key, rejects duplicate message_ids,
    stores the message, creates an Emergency for SOS messages, and
    broadcasts it over WebSocket."""
    return await process_gateway_message(db, payload)
