/**
 * Leaflet map helpers: typed marker icons + shared init. Requires Leaflet
 * to already be loaded (CDN script tag) before this file runs.
 */
const NaviXMap = (() => {
  const ICONS = {
    medical: "🚑",
    police: "👮",
    water: "💧",
    food: "🍲",
    help_centre: "🛈",
    ambulance: "🚑",
    toilet: "🚻",
    volunteer: "🧭",
    emergency: "🆘",
    user: "📍",
    gateway: "📶",
  };

  const COLORS = {
    medical: "#e02424",
    police: "#1e88e5",
    water: "#12a3c4",
    food: "#ff6b35",
    help_centre: "#1c9d5b",
    ambulance: "#e02424",
    toilet: "#5b667a",
    volunteer: "#0b2545",
    emergency: "#e02424",
    user: "#1e88e5",
    gateway: "#6a1b9a",
  };

  function divIcon(type, opts = {}) {
    const emoji = ICONS[type] || "📌";
    const color = COLORS[type] || "#0b2545";
    const size = opts.size || 34;
    return L.divIcon({
      className: "navix-marker",
      html: `<div style="
        width:${size}px;height:${size}px;border-radius:50%;
        background:${color};display:flex;align-items:center;justify-content:center;
        box-shadow:0 2px 8px rgba(0,0,0,0.35);border:2px solid #fff;
        font-size:${size * 0.5}px;">${emoji}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      popupAnchor: [0, -size / 2],
    });
  }

  function initMap(elementId, center, zoom = 15) {
    const map = L.map(elementId).setView([center.lat, center.lon], zoom);
    // Standard OpenStreetMap tiles. NOTE: these tiles require a live network
    // connection -- they are NOT cached for offline use. A pre-cached /
    // simplified offline tile pack can be swapped in here later (spec
    // section 7); the rest of the map code would not need to change.
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
    return map;
  }

  function facilityStatusBadge(status) {
    const cls = status === "open" ? "badge-open" : "badge-closed";
    const label = status === "open" ? "Open" : "Closed";
    return `<span class="badge ${cls}">${label}</span>`;
  }

  function facilityTypeLabel(type) {
    const labels = {
      medical: "Medical Camp",
      police: "Police Post",
      water: "Water Station",
      food: "Food Point",
      help_centre: "Help Centre",
      ambulance: "Ambulance",
      toilet: "Toilet",
    };
    return labels[type] || type;
  }

  return { ICONS, COLORS, divIcon, initMap, facilityStatusBadge, facilityTypeLabel };
})();
