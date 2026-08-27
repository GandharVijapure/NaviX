/**
 * Client-side waypoint navigation engine (spec sections 10-12/94). Mirrors
 * backend/services/navigation_service.py's math in JS so arrow-mode
 * guidance keeps working with zero network access once a route has been
 * downloaded into IndexedDB -- this is the "must not depend on live map
 * tiles" primary navigation mode.
 */
const NaviXNavEngine = (() => {
  const EARTH_RADIUS_KM = 6371.0088;
  const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  const CROWD_WALK_M_PER_MIN = 50;

  function toRad(deg) { return (deg * Math.PI) / 180; }

  function haversineKm(lat1, lon1, lat2, lon2) {
    const dPhi = toRad(lat2 - lat1);
    const dLambda = toRad(lon2 - lon1);
    const a = Math.sin(dPhi / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLambda / 2) ** 2;
    return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function bearingDeg(lat1, lon1, lat2, lon2) {
    const dLambda = toRad(lon2 - lon1);
    const y = Math.sin(dLambda) * Math.cos(toRad(lat2));
    const x = Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) - Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLambda);
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  }

  function compassOf(bearing) {
    return COMPASS[Math.round(bearing / 45) % 8];
  }

  function directionsTo(userLat, userLon, destLat, destLon) {
    const distanceKm = haversineKm(userLat, userLon, destLat, destLon);
    const bearing = bearingDeg(userLat, userLon, destLat, destLon);
    return {
      distance_m: Math.round(distanceKm * 1000 * 10) / 10,
      distance_km: Math.round(distanceKm * 1000) / 1000,
      bearing_deg: Math.round(bearing * 10) / 10,
      compass_direction: compassOf(bearing),
      estimated_walk_minutes: Math.round((distanceKm * 1000 / CROWD_WALK_M_PER_MIN) * 10) / 10,
    };
  }

  /** Finds the nearest not-yet-passed waypoint to the user, given a route's
   * ordered waypoint list, then returns guidance toward it (and the one
   * after it, for the "Next:" line). Waypoints are assumed already sorted
   * by `sequence`. */
  function guidanceAlongRoute(userLat, userLon, waypoints, arrivalRadiusM = 40) {
    if (!waypoints || waypoints.length === 0) return null;

    // Find the closest waypoint the user hasn't already reached, walking
    // forward from the first one whose distance exceeds the arrival radius.
    let targetIndex = waypoints.findIndex((wp) => haversineKm(userLat, userLon, wp.latitude, wp.longitude) * 1000 > arrivalRadiusM);
    if (targetIndex === -1) targetIndex = waypoints.length - 1; // arrived at the last one

    const target = waypoints[targetIndex];
    const next = waypoints[targetIndex + 1] || null;
    const dir = directionsTo(userLat, userLon, target.latitude, target.longitude);

    return {
      ...dir,
      instruction: target.instruction || "Continue Straight",
      landmark: target.landmark || null,
      next_landmark: next ? next.landmark || next.instruction : null,
      waypoint_index: targetIndex,
      waypoint_count: waypoints.length,
      is_final: targetIndex === waypoints.length - 1,
    };
  }

  return { haversineKm, bearingDeg, compassOf, directionsTo, guidanceAlongRoute };
})();
