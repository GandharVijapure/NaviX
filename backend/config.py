"""
Centralized configuration, read from environment variables with safe
development defaults. Nothing here is a real secret -- every default is
clearly a placeholder meant to be overridden in a real deployment.
"""
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./navix.db")

# --- Auth -------------------------------------------------------------
SECRET_KEY = os.getenv("NAVIX_SECRET_KEY", "navix-dev-secret-change-me-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))

# --- Gateway / hardware ingestion --------------------------------------
# A real ESP32/LoRa gateway (or the developer simulator) sends this value in
# the `X-NaviX-Gateway-Key` header. The default is a documented demo key --
# fine for a student prototype, NOT for a real deployment.
GATEWAY_API_KEY = os.getenv("NAVIX_GATEWAY_API_KEY", "navix-demo-gateway-key")

# --- CORS ---------------------------------------------------------------
# Comma-separated origins, e.g. "https://navix.example.com,https://admin.example.com"
_cors_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = ["*"] if _cors_env.strip() == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]

# A device/gateway is considered offline once its last heartbeat is older
# than this many seconds (spec section 26 -- "mark a device offline if
# heartbeat becomes sufficiently stale", computed on read, no task queue).
DEVICE_STALE_SECONDS = int(os.getenv("NAVIX_DEVICE_STALE_SECONDS", "45"))

APP_VERSION = "1.1.0"
