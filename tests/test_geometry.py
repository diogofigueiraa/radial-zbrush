import math

import pytest

from radial import geometry as g


def test_slot_zero_is_on_top():
    x, y = g.slot_position(0, 8, 100)
    assert x == pytest.approx(0, abs=1e-9)
    assert y == pytest.approx(-100)


def test_slots_go_clockwise():
    # Com y para baixo, o slot 2 de 8 (90° depois do topo) fica à direita.
    x, y = g.slot_position(2, 8, 100)
    assert x == pytest.approx(100)
    assert y == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("n", [3, 4, 5, 6, 8, 12, 16])
def test_center_of_each_slot_hits_itself(n):
    for i in range(n):
        x, y = g.slot_position(i, n, 100)
        assert g.hit_test(x, y, n, inner_radius=30) == i


@pytest.mark.parametrize("n", [4, 8])
def test_sector_boundaries(n):
    sector = 360 / n
    for i in range(n):
        base = g.slot_angle(i, n)
        for offset in (-sector / 2 + 0.5, sector / 2 - 0.5):
            a = math.radians(base + offset)
            assert g.angle_to_slot(math.cos(a), math.sin(a), n) == i


def test_dead_zone_and_outer_limit():
    assert g.hit_test(5, 5, 8, inner_radius=30) is None
    assert g.hit_test(0, -200, 8, inner_radius=30, outer_radius=150) is None
    assert g.hit_test(0, -100, 8, inner_radius=30, outer_radius=150) == 0


def test_flick():
    assert not g.is_flick(0, -100, 150)
    assert g.is_flick(0, -160, 150)


def test_invalid_count():
    assert g.hit_test(10, 10, 0, 1) is None
    with pytest.raises(ValueError):
        g.sector_size(0)
