"""Single source of truth for rainy-day effective width.

Every consumer (days API validation, allocation engine input, run
fingerprint) must go through this module — never multiply the coefficient
inline — so the集日 page, 切空引擎， 主图右端， 放不下 set and run drawer all
share one effective width.
"""
from __future__ import annotations

import hashlib
import json
import math

COEFF_MIN = 0.0
COEFF_MAX = 1.0
ROUND_DECIMALS = 3
_EPS = 1e-9


def validate_day_settings(rainy: bool, width_coefficient: float | None) -> None:
    """Raise ValueError (Chinese message) if the day settings are invalid."""
    if not rainy:
        return  # coefficient is ignored (stored NULL) on sunny days
    if width_coefficient is None:
        raise ValueError("雨天必须填写宽度系数")
    coeff = float(width_coefficient)
    if not math.isfinite(coeff):
        raise ValueError("雨天宽度系数必须为有限数字")
    # 0 is legal: effective width becomes 0 and every vendor is rejected.
    if coeff < COEFF_MIN - _EPS or coeff > COEFF_MAX + _EPS:
        raise ValueError("雨天宽度系数必须为 0 到 1 之间的数字")


def effective_width_m(registered_width_m: float, rainy: bool,
                      width_coefficient: float | None) -> float:
    """Usable right end: sunny = registered width; rainy = registered × coefficient."""
    registered = float(registered_width_m)
    if not rainy:
        return round(registered, ROUND_DECIMALS)
    validate_day_settings(True, width_coefficient)
    return round(registered * float(width_coefficient), ROUND_DECIMALS)


def config_fingerprint(*, registered_width_m: float, rainy: bool,
                       width_coefficient: float | None,
                       pillars: list[dict], vendors: list[dict]) -> str:
    """Stable hash of every allocation input; a change forces a fresh run."""
    normalized_pillars = sorted(
        (
            {
                "id": p.get("id"),
                "position_m": round(float(p["position_m"]), ROUND_DECIMALS),
                "thickness_m": round(float(p.get("thickness_m", 0.4)), ROUND_DECIMALS),
            }
            for p in pillars
        ),
        key=lambda p: (p["id"] is None, p["id"]),
    )
    normalized_vendors = sorted(
        (
            {
                "id": v["id"],
                "stall_width_m": round(float(v["stall_width_m"]), ROUND_DECIMALS),
                "priority": int(v.get("priority", 1)),
            }
            for v in vendors
        ),
        key=lambda v: v["id"],
    )
    coeff = (round(float(width_coefficient), 6)
             if width_coefficient is not None else None)
    payload = {
        "rainy": bool(rainy),
        "width_coefficient": coeff,
        "segment_width_m": round(float(registered_width_m), ROUND_DECIMALS),
        "pillars": normalized_pillars,
        "vendors": normalized_vendors,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
