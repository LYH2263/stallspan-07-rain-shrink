import math
import pytest

from app.services.day_settings import (
    config_fingerprint,
    effective_width_m,
    validate_day_settings,
)


def test_sunny_ignores_coefficient_even_if_present():
    validate_day_settings(False, None)  # no error
    validate_day_settings(False, 99.0)  # coefficient ignored entirely
    assert effective_width_m(30.0, False, 99.0) == 30.0
    assert effective_width_m(30.0, False, None) == 30.0


def test_rainy_requires_coefficient():
    with pytest.raises(ValueError, match="雨天必须填写宽度系数"):
        validate_day_settings(True, None)


@pytest.mark.parametrize("bad", [-0.1, 1.0001, float("nan"), float("inf"), float("-inf")])
def test_rainy_rejects_non_finite_or_out_of_range(bad):
    with pytest.raises(ValueError):
        validate_day_settings(True, bad)


@pytest.mark.parametrize("good", [0.0, 0.8, 1.0])
def test_rainy_accepts_zero_through_one(good):
    validate_day_settings(True, good)  # no error


def test_zero_coefficient_means_zero_width():
    assert effective_width_m(30.0, True, 0.0) == 0.0


def test_one_coefficient_keeps_registered_width():
    assert effective_width_m(30.0, True, 1.0) == 30.0


def test_seed_rainy_effective_width_is_24():
    assert effective_width_m(30.0, True, 0.8) == 24.0


def test_fingerprint_stable_under_input_reorder():
    pillars = [
        {"id": 1, "position_m": 10.0, "thickness_m": 0.5},
        {"id": 2, "position_m": 20.0, "thickness_m": 0.5},
    ]
    vendors = [
        {"id": 1, "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "stall_width_m": 3.0, "priority": 1},
    ]
    kwargs = dict(registered_width_m=30.0, rainy=True, width_coefficient=0.8,
                  pillars=pillars, vendors=vendors)
    a = config_fingerprint(**kwargs)
    b = config_fingerprint(**{**kwargs, "pillars": list(reversed(pillars)),
                              "vendors": list(reversed(vendors))})
    assert a == b


def test_fingerprint_changes_when_any_input_changes():
    base = dict(registered_width_m=30.0, rainy=True, width_coefficient=0.8,
                pillars=[{"id": 1, "position_m": 10.0, "thickness_m": 0.5}],
                vendors=[{"id": 1, "stall_width_m": 4.0, "priority": 1}])
    a = config_fingerprint(**base)
    assert config_fingerprint(**{**base, "rainy": False, "width_coefficient": None}) != a
    assert config_fingerprint(**{**base, "width_coefficient": 0.7}) != a
    assert config_fingerprint(**{**base, "registered_width_m": 29.0}) != a
    assert config_fingerprint(**{**base,
              "pillars": [{"id": 1, "position_m": 11.0, "thickness_m": 0.5}]}) != a
    assert config_fingerprint(**{**base,
              "vendors": [{"id": 1, "stall_width_m": 4.5, "priority": 1}]}) != a
