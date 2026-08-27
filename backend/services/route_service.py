"""
Helpers for pre-stored Wari routes (spec sections 10-12): total distance
computation and version bumping. Route *content* (which waypoints exist) is
simple CRUD handled directly in routers/routes.py; this module only holds
the bits worth sharing/testing in isolation.
"""
from typing import Sequence

from .location_service import haversine_distance_km


def total_distance_km(waypoints: Sequence) -> float:
    """Sums Haversine distance between consecutive waypoints (already
    ordered by `sequence`)."""
    if len(waypoints) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(waypoints, waypoints[1:]):
        total += haversine_distance_km(a.latitude, a.longitude, b.latitude, b.longitude)
    return round(total, 3)
