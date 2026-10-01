import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AllocationRun, MarketDay, Pillar, Segment, Vendor
from app.services.day_settings import config_fingerprint, effective_width_m
from app.services.first_fit_engine import allocate_first_fit, result_to_dict
router = APIRouter(prefix="/allocate", tags=["allocate"])


def _load_inputs(segment_id: int, db: Session):
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    day = db.get(MarketDay, seg.market_day_id)
    if not day:
        raise HTTPException(404, "集日不存在")
    pillar_rows = db.scalars(
        select(Pillar).where(Pillar.segment_id == segment_id).order_by(Pillar.id)
    ).all()
    pillars = [{"id": p.id, "position_m": p.position_m,
                "thickness_m": p.thickness_m, "label": p.label} for p in pillar_rows]
    vendor_rows = db.scalars(
        select(Vendor).where(Vendor.market_day_id == seg.market_day_id).order_by(Vendor.id)
    ).all()
    vendors = [{"id": v.id, "name": v.name, "stall_width_m": v.stall_width_m,
                "priority": v.priority} for v in vendor_rows]
    return seg, day, pillars, vendors


def _create_run(seg, day, pillars, vendors, db: Session) -> dict:
    """Compute at the CURRENT effective width and append an immutable snapshot row."""
    eff = effective_width_m(seg.width_m, day.rainy, day.width_coefficient)
    result = result_to_dict(allocate_first_fit(eff, vendors, pillars))
    result["segment"] = {"id": seg.id, "name": seg.name, "width_m": seg.width_m}
    result["day"] = {"id": day.id, "rainy": bool(day.rainy),
                     "width_coefficient": day.width_coefficient}
    result["effective_width_m"] = eff
    result["config_fingerprint"] = config_fingerprint(
        registered_width_m=seg.width_m, rainy=day.rainy,
        width_coefficient=day.width_coefficient, pillars=pillars, vendors=vendors)
    run = AllocationRun(segment_id=seg.id, created_at=datetime.utcnow(),
                        result_json=json.dumps(result, ensure_ascii=False))
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, **result}


@router.post("/run")
def run_allocate(segment_id: int = 1, db: Session = Depends(get_db)):
    seg, day, pillars, vendors = _load_inputs(segment_id, db)
    return _create_run(seg, day, pillars, vendors, db)


@router.get("/latest")
def latest(segment_id: int = 1, db: Session = Depends(get_db)):
    seg, day, pillars, vendors = _load_inputs(segment_id, db)
    run = db.scalars(select(AllocationRun).where(AllocationRun.segment_id == segment_id)
                     .order_by(AllocationRun.id.desc())).first()
    if not run:
        return _create_run(seg, day, pillars, vendors, db)
    data = json.loads(run.result_json)
    fingerprint = config_fingerprint(
        registered_width_m=seg.width_m, rainy=day.rainy,
        width_coefficient=day.width_coefficient, pillars=pillars, vendors=vendors)
    # Re-allocation must follow the new effective width and never eat the
    # pre-change cache. A mismatch (also for legacy rows lacking the key)
    # APPENDS a new run; the old row is never rewritten, so its right end
    # cannot be back-brushed by the new coefficient. (Two concurrent first
    # GETs may double-insert; the second then fingerprint-matches — harmless.)
    if data.get("config_fingerprint") != fingerprint:
        return _create_run(seg, day, pillars, vendors, db)
    return {"id": run.id, **data}


def _run_summary(run: AllocationRun) -> dict:
    data = json.loads(run.result_json)
    segment = data.get("segment", {})
    day_snap = data.get("day", {})
    registered = segment.get("width_m")
    eff = data.get("effective_width_m", registered)
    return {
        "id": run.id,
        "created_at": run.created_at.isoformat(),
        "rainy": bool(day_snap.get("rainy", False)),
        "width_coefficient": day_snap.get("width_coefficient"),
        "registered_width_m": registered,
        "effective_width_m": eff,
        "rejected_count": len(data.get("rejected", [])),
    }


@router.get("/runs")
def list_runs(segment_id: int = 1, db: Session = Depends(get_db)):
    rows = db.scalars(select(AllocationRun).where(AllocationRun.segment_id == segment_id)
                      .order_by(AllocationRun.id.desc())).all()
    return [_run_summary(r) for r in rows]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AllocationRun, run_id)
    if not run:
        raise HTTPException(404, "运行记录不存在")
    return {"id": run.id, **json.loads(run.result_json)}
