from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import MarketDay
from app.schemas.day import DayUpdate, day_to_dict
from app.services.day_settings import validate_day_settings

router = APIRouter(prefix="/days", tags=["days"])

@router.get("")
def list_days(db: Session = Depends(get_db)):
    return [day_to_dict(r) for r in
            db.scalars(select(MarketDay).order_by(MarketDay.id)).all()]

@router.patch("/{day_id}")
def update_day(day_id: int, payload: DayUpdate, db: Session = Depends(get_db)):
    day = db.get(MarketDay, day_id)
    if not day:
        raise HTTPException(status_code=404, detail="集日不存在")
    # Validate BEFORE touching the row: an invalid save must leave every
    # consumer (集日页/主图/放不下) on the previous values.
    try:
        validate_day_settings(payload.rainy, payload.width_coefficient)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    day.rainy = payload.rainy
    day.width_coefficient = float(payload.width_coefficient) if payload.rainy else None
    db.commit()
    db.refresh(day)
    return day_to_dict(day)
