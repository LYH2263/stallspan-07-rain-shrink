from __future__ import annotations

from pydantic import BaseModel


class DayUpdate(BaseModel):
    rainy: bool
    width_coefficient: float | None = None


def day_to_dict(day) -> dict:
    """Shared serializer for GET and PATCH /days."""
    return {
        "id": day.id,
        "name": day.name,
        "day": day.day.isoformat(),
        "rainy": bool(day.rainy),
        "width_coefficient": day.width_coefficient,
    }
