# NaviX

**Connecting Every Step, Even Without Networks.**

NaviX is an emergency communication, navigation, and coordination system for large public
gatherings — Wari, Kumbh Mela, processions, concerts, stadium events, and disaster-response
scenarios. It's built for the moment cellular networks buckle under crowd load: volunteers
carrying ESP32 + SX1278 LoRa + GPS devices form a mesh network that keeps SOS requests,
locations, and announcements flowing back to a control room even without internet coverage.

This repository is a working full-stack prototype. The physical LoRa hardware isn't required
to demo it — a backend-driven simulator stands in for the field devices so the entire
workflow (SOS → volunteer assignment → resolution) can be shown end-to-end today.

## Architecture

```text
WARKARI / PUBLIC USER
          |
     NaviX PWA  (static HTML/CSS/JS, Bootstrap 5, Leaflet)
          |
   FastAPI Backend  (REST + WebSocket, JWT auth)
          |
      SQLite  (swap to PostgreSQL via DATABASE_URL)
          |
--------------------------------
|                              |
Control Room              LoRa Gateway
                               |
                          ESP32 + LoRa
                               |
                       Volunteer Devices
```

Hardware pathway (future — see "Future ESP32 Integration" below):

```text
Volunteer Device (ESP32 + GPS + LoRa)
        -> LoRa Mesh
        -> Main Volunteer / Gateway Node
        -> Python FastAPI Server (/api/device/*)
        -> Control Room Dashboard
        -> Police / Ambulance / Medical Team
```

## Features

- **Pilgrim (no login required):** nearby medical/police/water/food/help-centre facilities
  with live distance, simplified compass-style navigation, SOS button, community
  announcements, lost-person reporting and browsing, last-known-location caching.
- **Volunteer (login required):** profile, live status (Available/Responding/Busy/Offline),
  nearby SOS requests, nearby volunteers/facilities, live map.
- **Control Room / Authority (login required):** stat dashboard, live map of every
  volunteer/emergency/facility, emergency assignment + status pipeline
  (NEW → ACKNOWLEDGED → RESPONDER_ASSIGNED → RESPONDING → RESOLVED), volunteer/device
  rosters, facility CRUD, announcement publishing, lost-person status updates, lightweight
  analytics, and a one-click demo simulator toggle.
- **Hardware simulator:** a developer page that calls the exact same `/api/device/*`
  endpoints a real ESP32 base station will use later.
- **Real-time:** a single WebSocket channel (`/ws`) pushes SOS creation, emergency status
  changes, volunteer/device updates, new announcements, facility changes, and lost-person
  status changes to every connected screen.
- **PWA:** installable, caches the app shell + last-fetched facility/announcement data, shows
  an "Offline Mode Active" banner when the server is unreachable. (OpenStreetMap tiles
  themselves are NOT cached for offline use — that needs a pre-cached tile pack, left as a
  documented extension point.)
- **Multilingual architecture:** English (complete), Hindi and Marathi (partial) with a
  transparent fallback to English for any missing key.

## Technology Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, WebSockets, JWT (python-jose),
  bcrypt password hashing.
- **Database:** SQLite for development. Swapping to PostgreSQL only requires changing the
  `DATABASE_URL` environment variable — no code depends on SQLite-specific SQL.
- **Frontend:** plain HTML5/CSS3/JavaScript (no build step), Bootstrap 5, Leaflet.js +
  OpenStreetMap, Fetch API, native WebSocket client, a small service worker for PWA caching.

## Folder Structure

```text
navix/
├── requirements.txt
├── README.md
├── backend/
│   ├── main.py                # FastAPI app, routing, static mounts, startup seed
│   ├── database.py            # SQLAlchemy engine/session
│   ├── models.py               # ORM models
│   ├── schemas.py               # Pydantic request/response models
│   ├── auth.py                  # JWT + bcrypt + role guards
│   ├── websocket_manager.py     # WebSocket broadcast manager
│   ├── seed.py                  # Demo data generator (idempotent)
│   ├── simulator.py             # Demo-mode background mover/heartbeat
│   ├── routers/                 # auth, facilities, volunteers, devices, emergencies,
│   │                            #   announcements, lost_persons, navigation, admin
│   ├── services/                # location_service, navigation_service, notification_service
│   └── static/uploads/          # lost-person photo uploads
└── frontend/
    ├── manifest.json, service-worker.js, offline.html
    ├── css/style.css
    ├── js/                       # api, auth, ws, geo, map, i18n, layout, pwa-register
    ├── i18n/en.json, hi.json, mr.json
    ├── icons/icon.svg
    └── pages/                    # one HTML file per route (see "Routes" below)
```

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

Nothing to do manually — on first run, `backend/main.py`'s startup hook creates all tables
(`Base.metadata.create_all`) and seeds demo data (10 volunteers, 5 medical camps, 4 police
posts, 6 water/food points, 3 emergencies, 3 announcements, 4 lost-person reports) if the
`users` table is empty. Delete `navix.db` to reset and reseed.

## Running the Backend

From the `navix/` project root (so `backend` resolves as a package):

```bash
uvicorn backend.main:app --reload
```

## Opening the Application

The FastAPI app also serves the frontend, so once the server is running just open:

- **Public site:** http://127.0.0.1:8000/
- **Pilgrim home:** http://127.0.0.1:8000/find-help
- **Volunteer login:** http://127.0.0.1:8000/volunteer/login (demo: `volunteer1` / `volunteer123`)
- **Control room login:** http://127.0.0.1:8000/admin/login (demo: `admin` / `admin123`)
- **Hardware simulator:** http://127.0.0.1:8000/developer/device-simulator

## Accessing Swagger API Docs

```text
http://127.0.0.1:8000/docs
```

Endpoints are grouped by tag: Auth, Facilities, Volunteers, Devices, Emergencies,
Announcements, Lost Persons, Navigation, Admin/Analytics. To call a protected endpoint from
Swagger: log in via `POST /api/auth/login`, copy the `access_token`, click **Authorize**, and
paste the token (Bearer scheme).

## Using the Simulator

Two complementary ways to demo the "hardware" layer without physical ESP32/LoRa devices:

1. **One-click demo mode** — click **▶ Start NaviX Simulation** on the control-room dashboard
   or the developer simulator page. Every few seconds, seeded volunteers drift slightly,
   device heartbeats refresh, battery levels jitter, and occasionally a random demo
   emergency appears — all pushed live over WebSocket.
2. **Manual hardware simulator** (`/developer/device-simulator`) — POSTs directly to
   `/api/device/location`, `/api/device/sos`, `/api/device/status`, and
   `/api/device/heartbeat`, exactly as a real ESP32 base station will later.

## Demo Workflow

1. Open `/sos` (or `/find-help` → Emergency SOS) as a pilgrim and send an SOS.
2. Open `/admin/login`, sign in as `admin`, and watch it appear on `/admin/dashboard` and
   `/admin/emergencies` without a page refresh.
3. Assign the nearest volunteer and progress the status
   NEW → ACKNOWLEDGED → RESPONDER_ASSIGNED → RESPONDING → RESOLVED.
4. Open `/volunteer/dashboard` (as `volunteer1`) to see the same emergency and change status.

## Future ESP32 Integration

The `/api/device/*` router is intentionally hardware-agnostic: `POST /api/device/location`,
`/sos`, `/status`, `/heartbeat`, and `GET /api/device/commands` accept/return the same JSON
shapes a real ESP32 + SX1278 LoRa + GPS unit will send once connected — only the sender
changes from the simulator page to a LoRa gateway relaying real mesh traffic. No frontend or
database changes are needed to make that swap.

## Deliberately Deferred (Future Development)

Per the project's phased scope, the following are architected for but not implemented yet:
AI crowd-density prediction, drone-deployed mesh nodes, voice communication over LoRa,
advanced mesh routing algorithms, state disaster-management integration, solar telemetry
optimization, and wearable hardware.
