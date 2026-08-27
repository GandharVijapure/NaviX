# NaviX

**Connecting Every Step, Even Without Networks.**

NaviX is an emergency communication, offline navigation, missing-person coordination, public
information, and field-response system built for large public gatherings — Wari, Kumbh Mela,
processions, concerts, stadium events, and disaster-response scenarios — where cellular
networks become overloaded or unavailable.

This repository is a working full-stack prototype. Real ESP32 + SX1278 LoRa + GPS hardware
isn't required to demo it — a developer-facing simulator drives the same production-style
APIs real field devices will use, so the entire workflow (SOS → mesh relay → control room →
authority → resolution) can be shown end-to-end today.

## Architecture

NaviX is a hybrid system across four layers:

```text
Layer 1 — Warkari/User          NaviX Companion PWA (works offline, no login required)
Layer 2 — Field Emergency Net   Sub-Volunteers → LoRa nodes → multi-hop mesh → Main Gateway
Layer 3 — Communication+Backend Bluetooth → Internet → FastAPI Ground Station → DB → WebSockets
Layer 4 — Authority              Ground Station Control Room → Police/Medical/Crowd/Disaster/
                                  Missing-Person teams → Response Teams
```

Forward path (an emergency reaching the control room):

```text
Sub-Volunteer → LoRa Node → Multi-Hop Relay → Main Gateway → Bluetooth → Gateway Phone
  → Internet → NaviX FastAPI Backend → Database → WebSocket → Ground Station
  → Operator Verification → Priority → Responder/Authority Assignment → Response Team
```

Reverse path (an announcement reaching pilgrims):

```text
Ground Station → NaviX Backend → Database → WebSocket/API → Internet → Companion App → Warkari
```

A visual version of this lives at `/developer/architecture` once the server is running.

**Important, accurate claims** (see also `/developer/architecture`):
- LoRa itself is *not* a mesh protocol — NaviX implements/records application-level multi-hop
  forwarding on top of it (`origin_node`/`previous_hop`/`hop_count`/`message_id` dedup).
- OpenStreetMap tiles need a live connection and are never claimed to work offline. Offline
  navigation instead uses pre-downloaded route waypoints (arrow/compass guidance, no map
  tiles required).
- A public smartphone SOS needs internet unless a future LoRa hardware bridge exists; when
  offline, it's queued locally (IndexedDB) and synced automatically once connectivity returns.
- LoRa node spacing/range is never promised as a fixed number (e.g. "1-2 km") — real range
  depends on antenna, power, terrain, crowd density and interference.

## What's Implemented vs. Simulated

| Real, working code | Simulated / future hardware |
|---|---|
| FastAPI backend, SQLAlchemy models, JWT auth, bcrypt hashing | Actual LoRa RF transmission / real multi-hop mesh routing |
| WebSocket live updates across every dashboard | Bluetooth link between a field node and the gateway phone |
| Facilities, SOS, lost-person, announcements, routes, authorities, dispatch, gateway-ingestion APIs | ESP32 firmware itself (device-side code) |
| PWA offline caching (IndexedDB + service worker) + background sync of queued SOS/reports | Real government/authority system integrations |
| Waypoint arrow-mode navigation, fully offline once a route is downloaded | AI crowd-density prediction, facial recognition, drones, voice-over-LoRa, full offline map tiles |

## Technology Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, WebSockets, JWT (python-jose),
  bcrypt password hashing (used directly, not via passlib — see note in `backend/auth.py`).
- **Database:** SQLite for development. Swapping to PostgreSQL only requires changing the
  `DATABASE_URL` environment variable in `backend/config.py` — no SQLite-specific SQL anywhere.
- **Frontend:** plain HTML5/CSS3/JavaScript (no build step), Bootstrap 5, Leaflet.js +
  OpenStreetMap, Fetch API, native WebSocket client, IndexedDB, a service worker for PWA
  caching.

## Folder Structure

```text
navix/
├── requirements.txt
├── README.md
├── backend/
│   ├── main.py                # FastAPI app, routing, static mounts, startup seed, /api/health
│   ├── config.py               # centralized env-driven configuration
│   ├── database.py             # SQLAlchemy engine/session
│   ├── models.py                # ORM models (13 tables, see below)
│   ├── schemas.py               # Pydantic request/response models, incl. field validation
│   ├── auth.py                  # JWT + bcrypt + role guards + gateway API-key guard
│   ├── websocket_manager.py     # Standardized {event,data,timestamp} broadcast manager
│   ├── seed.py                  # Demo data generator (idempotent)
│   ├── simulator.py             # Demo-mode background mover/heartbeat (volunteers + gateway)
│   ├── routers/                 # auth, facilities, routes, volunteers, devices, gateways,
│   │                            #   emergencies, announcements, lost_persons, authorities,
│   │                            #   dispatches, navigation, admin
│   ├── services/                # location_service, navigation_service, emergency_service,
│   │                            #   gateway_service, route_service, notification_service
│   └── static/uploads/          # lost-person photo uploads
└── frontend/
    ├── manifest.json, service-worker.js, offline.html
    ├── css/style.css
    ├── js/                       # api, auth, ws, geo, map, i18n, layout, pwa-register,
    │                             #   offline-db (IndexedDB), sync-manager, navigation-engine
    ├── i18n/en.json, hi.json, mr.json
    ├── icons/icon.svg
    └── pages/                    # one HTML file per route (see "Routes" below)
```

### Database models

`users`, `volunteers`, `devices`, `facilities`, `emergencies`, `emergency_events`,
`announcements`, `lost_persons`, `gateways`, `lora_messages`, `authorities`, `dispatches`,
`routes`, `route_waypoints`. Tables are created via `SQLAlchemy.metadata.create_all()` at
startup — simple for this project's scope, but structured so Alembic migrations can be added
later without a rewrite. **If you pull a schema change, delete `navix.db` and restart** — the
app never silently drops/migrates data, it only creates missing tables.

## Installation

```bash
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Database Setup

Nothing to do manually — on first run, `backend/main.py`'s startup hook creates all tables and
seeds demo data if the `users` table is empty: 10 volunteers, 5 medical camps, 4 police posts,
6 water/food points, 5 authorities, a gateway (`GW-01`) + 5 field mesh nodes (`NODE-01..05`),
1 pre-stored Wari route with waypoints, 3 emergencies, 3 announcements, 4 lost-person reports.
Delete `navix.db` to reset and reseed.

## Running the Backend

From the `navix/` project root (so `backend` resolves as a package):

```bash
uvicorn backend.main:app --reload
```

## Opening the Application

- **Public site:** http://127.0.0.1:8000/
- **Pilgrim home:** http://127.0.0.1:8000/find-help
- **Volunteer login:** http://127.0.0.1:8000/volunteer/login (demo: `volunteer1` / `volunteer123`)
- **Control room login:** http://127.0.0.1:8000/admin/login (demo: `admin` / `admin123`)
- **Hardware simulator:** http://127.0.0.1:8000/developer/device-simulator
- **Architecture overview:** http://127.0.0.1:8000/developer/architecture

> **Development demo credentials only.** In a real deployment these accounts and the default
> `NAVIX_GATEWAY_API_KEY` must be replaced/rotated via environment variables, never hardcoded.

## Accessing Swagger API Docs

```text
http://127.0.0.1:8000/docs
```

Endpoints are grouped by tag: Auth, Facilities, Routes, Volunteers, Devices, Gateways,
Emergencies, Announcements, Lost Persons, Authorities, Dispatches, Navigation,
Admin/Analytics, System. To call a protected endpoint from Swagger: log in via
`POST /api/auth/login`, copy the `access_token`, click **Authorize**, paste it (Bearer
scheme). Gateway ingestion endpoints (`/api/gateway/*`) instead need the
`X-NaviX-Gateway-Key` header — the documented demo value is `navix-demo-gateway-key`.

## Using the Simulator

1. **One-click demo mode** — click **▶ Start NaviX Simulation** on the control-room dashboard
   or the developer simulator page. Volunteers drift, device/gateway heartbeats refresh,
   battery and RSSI/SNR jitter, and occasional random emergencies appear — all pushed live
   over WebSocket.
2. **Manual device simulator** (`/developer/device-simulator`) — POSTs to
   `/api/device/location|sos|status|heartbeat`, the same shapes a real ESP32 unit will send.
3. **Multi-hop gateway simulator** (same page) — the **"Send Demo Medical SOS"** button (and
   the manual form below it) POSTs to `POST /api/gateway/messages` with
   `origin_node`/`previous_hop`/`hop_count`/`rssi`/`snr`, demonstrating the
   NODE-05 → NODE-04 → NODE-03 → GW-01 relay path and server-side duplicate-message rejection.

## Offline Mode

- The service worker caches the app shell, CSS/JS, and the last-fetched facility/announcement
  API responses.
- `frontend/js/offline-db.js` (IndexedDB) additionally caches facilities, announcements,
  downloaded routes, the last known GPS fix, and queues SOS/lost-person reports made while
  offline (each tagged with a `client_request_id` so a retried sync never creates a
  duplicate — the backend enforces uniqueness on that field).
- `frontend/js/sync-manager.js` listens for the `online` event and flushes the queue,
  re-downloads fresh facilities/announcements/routes, and dispatches a
  `navix:sync-status` event pages use to show "Connection restored — syncing data..." /
  "Data synchronized."
- `/navigation`'s **Saved Route** tab lets you download a pre-stored Wari route while online,
  then follow arrow/compass guidance computed entirely client-side
  (`frontend/js/navigation-engine.js`, mirroring the backend's Haversine/bearing math) with
  zero network access.

## Demo Workflows

**A — Multi-hop LoRa medical SOS:** open the developer simulator → click "Send Demo Medical
SOS" → watch it land instantly on `/admin/dashboard` and `/admin/emergencies` with its LoRa
provenance (origin node, hop count, RSSI/SNR) visible in the detail panel → assign the nearest
volunteer and/or dispatch to an authority → progress
NEW → ACKNOWLEDGED → RESPONDER_ASSIGNED → RESPONDING → RESOLVED.

**B — Public SOS:** open `/sos` as a pilgrim, send an SOS (or, offline, watch it queue and
sync once reconnected) → see it appear live in the control room.

**C — Reverse announcement:** create a **Critical** announcement on `/admin/announcements` →
watch the critical banner appear instantly on every public page via WebSocket.

**D — Lost person:** report someone missing (with or without a photo) on
`/lost-person/report` → see the card on `/lost-person` → update its status from
`/admin/lost-persons` through Missing → Possible Match → Found → Reunited.

## Future ESP32 Integration

`POST /api/gateway/messages` (API-key protected) and the legacy `POST /api/device/*` router
are both hardware-agnostic: they accept/return the same JSON shapes a real ESP32 + SX1278
LoRa + GPS gateway will send once connected — only the sender changes from the simulator page
to real field hardware. No frontend or database changes are needed to make that swap.

## Deliberately Deferred (Future Development)

AI crowd-density prediction, drone-deployed mesh nodes, voice communication over LoRa,
advanced (real) mesh routing algorithms, state disaster-management system integration, solar
telemetry optimization, wearable hardware, real-time push notifications, and facial-
recognition-based lost-person matching. The architecture (service layer, event schema,
device/gateway registry) is structured so these can be added without a rewrite.
