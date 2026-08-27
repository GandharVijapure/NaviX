"""
Geolocation math: Haversine distance + nearest-facility/volunteer lookups.

Kept dependency-free (pure math) so it's trivially unit-testable and has no
opinion about the DB layer beyond the plain objects/rows it's handed.
"""
import math
from typing import Iterable, Optional, Sequence

EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def nearest_items(
    user_lat: float,
    user_lon: float,
    items: Iterable[object],
    lat_attr: str = "latitude",
    lon_attr: str = "longitude",
    limit: Optional[int] = None,
) -> list[tuple[object, float]]:
    """Sort arbitrary objects (facilities, volunteers, ...) by distance from
    the user. Returns list of (item, distance_km) tuples, closest first."""
    scored = []
    for item in items:
        lat = getattr(item, lat_attr, None)
        lon = getattr(item, lon_attr, None)
        if lat is None or lon is None:
            continue
        distance = haversine_distance_km(user_lat, user_lon, lat, lon)
        scored.append((item, distance))
    scored.sort(key=lambda pair: pair[1])
    return scored[:limit] if limit else scored
