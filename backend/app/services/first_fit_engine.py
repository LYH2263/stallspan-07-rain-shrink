"""1D First-Fit stall placement along a street segment; stalls cannot cross pillars."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field

_EPS = 1e-9

@dataclass
class Placement:
    vendor_id: int
    vendor_name: str
    start_m: float
    end_m: float
    width_m: float

@dataclass
class Rejected:
    vendor_id: int
    vendor_name: str
    width_m: float
    reason: str

@dataclass
class PillarRect:
    """The pillar rectangle that actually participates in splitting spans."""
    pillar_id: int | None
    position_m: float
    thickness_m: float
    label: str
    start_m: float
    end_m: float

@dataclass
class AllocResult:
    placements: list[Placement]
    rejected: list[Rejected]
    free_spans: list[tuple[float, float]]
    pillar_rects: list[PillarRect] = field(default_factory=list)

def pillar_rects_for_width(width_m: float, pillars: list[dict]) -> list[PillarRect]:
    """Pillars participating at the given (possibly rain-shrunk) right end.

    Global strategy is 整根作废: if the pillar's meter mark position_m lies
    beyond the right end, the WHOLE pillar is dropped — it is never cropped
    to a sliver, even when its thickness overhangs the boundary. A pillar at
    or inside the end participates whole; its blocked interval is only
    clamped by the street edges [0, width_m].
    """
    rects: list[PillarRect] = []
    for p in pillars:
        pos = float(p["position_m"])
        thickness = float(p.get("thickness_m", 0.4))
        if pos > width_m + _EPS:
            continue  # 整根作废：米标超出缩后右端
        half = thickness / 2.0
        lo = max(0.0, pos - half)
        hi = min(width_m, pos + half)
        if hi - lo <= _EPS:
            continue
        rects.append(PillarRect(
            pillar_id=p.get("id"),
            position_m=round(pos, 3),
            thickness_m=round(thickness, 3),
            label=str(p.get("label") or "挡柱"),
            start_m=round(lo, 3),
            end_m=round(hi, 3),
        ))
    rects.sort(key=lambda r: r.start_m)
    return rects

def free_spans_from_pillars(width_m: float, pillars: list[dict]) -> list[tuple[float, float]]:
    """pillars: position_m, thickness_m — treated as blocked intervals."""
    blocked = [(r.start_m, r.end_m) for r in pillar_rects_for_width(width_m, pillars)]
    blocked.sort()
    merged = []
    for lo, hi in blocked:
        if not merged or lo > merged[-1][1]:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    spans = []
    cursor = 0.0
    for lo, hi in merged:
        if lo > cursor:
            spans.append((cursor, lo))
        cursor = hi
    if cursor < width_m:
        spans.append((cursor, width_m))
    return [(round(a, 3), round(b, 3)) for a, b in spans if b - a > 1e-6]

def allocate_first_fit(width_m: float, vendors: list[dict], pillars: list[dict]) -> AllocResult:
    """vendors sorted by priority ascending then id; each needs stall_width_m contiguous in one free span (no pillar cross)."""
    rects = pillar_rects_for_width(width_m, pillars)
    spans = free_spans_from_pillars(width_m, pillars)
    # mutable remaining capacity per span
    remain = [[a, b] for a, b in spans]
    ordered = sorted(vendors, key=lambda v: (v.get("priority", 1), v["id"]))
    placements: list[Placement] = []
    rejected: list[Rejected] = []
    for v in ordered:
        need = float(v["stall_width_m"])
        placed = False
        for span in remain:
            avail = span[1] - span[0]
            if avail + 1e-9 >= need:
                start = span[0]
                end = start + need
                placements.append(Placement(v["id"], v["name"], round(start, 3), round(end, 3), need))
                span[0] = end
                placed = True
                break
        if not placed:
            rejected.append(Rejected(v["id"], v["name"], need, "无连续空档可放下且不跨越挡柱"))
    free = [(round(a, 3), round(b, 3)) for a, b in remain if b - a > 1e-6]
    return AllocResult(placements, rejected, free, rects)

def result_to_dict(r: AllocResult) -> dict:
    return {
        "placements": [asdict(p) for p in r.placements],
        "rejected": [asdict(x) for x in r.rejected],
        "free_spans": [{"start_m": a, "end_m": b} for a, b in r.free_spans],
        "pillar_rects": [asdict(c) for c in r.pillar_rects],
    }
