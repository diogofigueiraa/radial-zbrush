"""Radial menu math: slot positions and which slot is under the cursor.

Convention: screen coordinates (x to the right, y down), relative to the
menu center. Slot 0 sits at the top and the rest follow clockwise.
"""

from __future__ import annotations

import math

START_DEG = -90.0  # top of the screen (y points down, so -90° points up)


def sector_size(n: int) -> float:
    """Size of each slice, in degrees."""
    if n <= 0:
        raise ValueError("n must be greater than zero")
    return 360.0 / n


def slot_angle(index: int, n: int) -> float:
    """Angle (in degrees) of the center of slot `index`."""
    return START_DEG + index * sector_size(n)


def slot_position(index: int, n: int, radius: float) -> tuple[float, float]:
    """Center of slot `index`, relative to the menu center."""
    a = math.radians(slot_angle(index, n))
    return (radius * math.cos(a), radius * math.sin(a))


def distance(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def angle_to_slot(dx: float, dy: float, n: int) -> int:
    """Index of the slice in the (dx, dy) direction, ignoring distance."""
    sector = sector_size(n)
    angle = math.degrees(math.atan2(dy, dx))
    rel = (angle - START_DEG + sector / 2.0) % 360.0
    return int(rel // sector) % n


def hit_test(
    dx: float,
    dy: float,
    n: int,
    inner_radius: float,
    outer_radius: float | None = None,
) -> int | None:
    """Slot under the cursor, or None inside the central dead zone
    (or beyond `outer_radius`, when given)."""
    if n <= 0:
        return None
    d = distance(dx, dy)
    if d < inner_radius:
        return None
    if outer_radius is not None and d > outer_radius:
        return None
    return angle_to_slot(dx, dy, n)


def is_flick(dx: float, dy: float, flick_radius: float) -> bool:
    """True when the cursor has moved past the flick radius."""
    return distance(dx, dy) >= flick_radius
