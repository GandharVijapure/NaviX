"""
Simplified straight-line "walking guidance" between a user and a facility.

This intentionally does NOT attempt real road/footpath routing (that needs
routed map data NaviX doesn't have yet -- see spec section 7/32). Instead it
gives a compass bearing + distance, which is the right level of detail for
the crowded-event "simple navigation mode" the spec asks for:

    ↑ Continue Straight
    120 m
    Then turn right

Swapping this for a real routing engine (OSRM, GraphHopper, etc.) later only
means replacing get_directions() -- callers only depend on DirectionsOut-
shaped data.
"""
import math

from .location_service import haversine_distance_km

# 8-point compass, matched to bearing_deg ranges of 45 degrees each.
_COMPASS_POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Very rough average walking speed in a dense crowd (metres/minute).
CROWD_WALKING_SPEED_M_PER_MIN = 50


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0-360, 0 = North) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def bearing_to_compass(bearing: float) -> str:
    index = round(bearing / 45) % 8
    return _COMPASS_POINTS[index]


def turn_hint(bearing: float, user_heading: float = 0.0) -> str:
    """Very simple turn hint relative to the user's current heading.
    When the browser doesn't provide a device heading, user_heading defaults
    to 0 (assume facing North) -- still useful as a compass-style hint."""
    relative = (bearing - user_heading + 360) % 360
    if relative <= 20 or relative >= 340:
        return "Continue Straight"
    if 20 < relative < 160:
        return "Turn Right"
    if 160 <= relative <= 200:
        return "Turn Around"
    return "Turn Left"


def get_directions(user_lat: float, user_lon: float, dest_lat: float, dest_lon: float, user_heading: float = 0.0) -> dict:
    distance_km = haversine_distance_km(user_lat, user_lon, dest_lat, dest_lon)
    distance_m = distance_km * 1000
    bearing = bearing_deg(user_lat, user_lon, dest_lat, dest_lon)
    return {
        "distance_m": round(distance_m, 1),
        "distance_km": round(distance_km, 3),
        "bearing_deg": round(bearing, 1),
        "compass_direction": bearing_to_compass(bearing),
        "turn_hint": turn_hint(bearing, user_heading),
        "estimated_walk_minutes": round(distance_m / CROWD_WALKING_SPEED_M_PER_MIN, 1),
    }
