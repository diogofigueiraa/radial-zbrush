"""Matemática do menu radial: posição dos slots e qual slot está sob o mouse.

Convenção: coordenadas de tela (x para a direita, y para baixo), relativas ao
centro do menu. O slot 0 fica no topo e os seguintes seguem no sentido horário.
"""

from __future__ import annotations

import math

START_DEG = -90.0  # topo da tela (y para baixo => -90° aponta para cima)


def sector_size(n: int) -> float:
    """Tamanho de cada fatia, em graus."""
    if n <= 0:
        raise ValueError("n precisa ser maior que zero")
    return 360.0 / n


def slot_angle(index: int, n: int) -> float:
    """Ângulo (em graus) do centro do slot `index`."""
    return START_DEG + index * sector_size(n)


def slot_position(index: int, n: int, radius: float) -> tuple[float, float]:
    """Centro do slot `index`, relativo ao centro do menu."""
    a = math.radians(slot_angle(index, n))
    return (radius * math.cos(a), radius * math.sin(a))


def distance(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def angle_to_slot(dx: float, dy: float, n: int) -> int:
    """Índice da fatia na direção (dx, dy), ignorando a distância."""
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
    """Slot sob o cursor, ou None se estiver na zona morta central
    (ou além de `outer_radius`, quando informado)."""
    if n <= 0:
        return None
    d = distance(dx, dy)
    if d < inner_radius:
        return None
    if outer_radius is not None and d > outer_radius:
        return None
    return angle_to_slot(dx, dy, n)


def is_flick(dx: float, dy: float, flick_radius: float) -> bool:
    """True quando o cursor saiu além do raio de flick."""
    return distance(dx, dy) >= flick_radius
