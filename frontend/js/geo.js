/**
 * Browser geolocation wrapper + "last known location" persistence (spec
 * section 3: pilgrims should keep their last location even without a fresh
 * GPS fix).
 */
const NaviXGeo = (() => {
  const LAST_LOC_KEY = "navix_last_location";
  // Fallback used only if geolocation is denied/unavailable AND no location
  // was ever cached -- centre of the seeded demo area, so the map still
  // shows something sensible on a fresh device.
  const FALLBACK = { lat: 18.5204, lon: 73.8567 };

  function getCached() {
    const raw = localStorage.getItem(LAST_LOC_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function save(lat, lon) {
    localStorage.setItem(LAST_LOC_KEY, JSON.stringify({ lat, lon, at: new Date().toISOString() }));
  }

  function getCurrentPosition() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(getCached() || FALLBACK);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          save(loc.lat, loc.lon);
          resolve(loc);
        },
        () => {
          resolve(getCached() || FALLBACK);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
      );
    });
  }

  return { getCurrentPosition, getCached, save, FALLBACK };
})();
