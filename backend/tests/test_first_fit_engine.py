from app.services.first_fit_engine import allocate_first_fit, free_spans_from_pillars, pillar_rects_for_width

SEED_PILLARS = [
    {"id": 1, "position_m": 10.0, "thickness_m": 0.5, "label": "灯柱A"},
    {"id": 2, "position_m": 20.0, "thickness_m": 0.5, "label": "灯柱B"},
]
SEED_VENDORS = [
    {"id": 1, "name": "阿强烧烤", "stall_width_m": 4.0, "priority": 1},
    {"id": 2, "name": "林记糖水", "stall_width_m": 3.0, "priority": 1},
    {"id": 3, "name": "老周水果", "stall_width_m": 5.0, "priority": 2},
    {"id": 4, "name": "小美饰品", "stall_width_m": 2.5, "priority": 2},
    {"id": 5, "name": "大碗面", "stall_width_m": 6.0, "priority": 1},
    {"id": 6, "name": "手作皮具", "stall_width_m": 3.5, "priority": 3},
    {"id": 7, "name": "巨型舞台车", "stall_width_m": 12.0, "priority": 9},
]

def test_free_spans_with_pillars():
    spans = free_spans_from_pillars(30.0, [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}])
    assert len(spans) == 3
    assert spans[0][0] == 0.0

def test_first_fit_no_cross_pillar():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 12.0, "priority": 1},
    ]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert any(p.vendor_name == "A" for p in r.placements)
    # 12m may fit in a free span after first placement depending on remainders
    assert len(r.placements) + len(r.rejected) == 2

def test_reject_oversized():
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert len(r.rejected) == 1
    assert r.rejected[0].vendor_name == "Huge"

# --- rainy effective width + 整根作废 pillar strategy ---

def test_pillar_mark_past_right_end_is_void_whole():
    # W = 24; a mark at 24.2 with half 0.25 overhangs the end (23.95 < 24)
    # but must be dropped WHOLE — never cropped to a [23.95, 24] sliver.
    rects = pillar_rects_for_width(24.0, [{"id": 9, "position_m": 24.2, "thickness_m": 0.5}])
    assert rects == []
    # and it must not split spans: a single full span remains
    assert free_spans_from_pillars(24.0, [{"position_m": 24.2, "thickness_m": 0.5}]) == [(0.0, 24.0)]

def test_pillar_far_past_right_end_is_void():
    rects = pillar_rects_for_width(24.0, [{"id": 9, "position_m": 30.0, "thickness_m": 0.5}])
    assert rects == []

def test_pillar_mark_exactly_at_right_end_participates():
    # position_m == W: whole pillar participates; interval clamps to the edge.
    rects = pillar_rects_for_width(24.0, [{"id": 9, "position_m": 24.0, "thickness_m": 0.5}])
    assert len(rects) == 1
    assert rects[0].start_m == 23.75
    assert rects[0].end_m == 24.0

def test_pillar_mark_inside_right_end_participates_whole():
    rects = pillar_rects_for_width(24.0, [{"id": 9, "position_m": 20.0, "thickness_m": 0.5}])
    assert len(rects) == 1
    assert (rects[0].start_m, rects[0].end_m) == (19.75, 20.25)

def test_rainy_24m_seed_scenario():
    r = allocate_first_fit(24.0, SEED_VENDORS, SEED_PILLARS)
    rejected_names = {x.vendor_name for x in r.rejected}
    assert rejected_names == {"老周水果", "巨型舞台车"}
    # both pillars are within 24m and participate; nothing extends past the right end
    assert len(r.pillar_rects) == 2
    assert all(p.end_m <= 24.0 for p in r.placements)
    # free spans: 9.75 / 9.5 / 3.75
    assert free_spans_from_pillars(24.0, SEED_PILLARS) == [(0.0, 9.75), (10.25, 19.75), (20.25, 24.0)]

def test_sunny_30m_seed_scenario_unchanged():
    r = allocate_first_fit(30.0, SEED_VENDORS, SEED_PILLARS)
    assert {x.vendor_name for x in r.rejected} == {"巨型舞台车"}
    assert len(r.pillar_rects) == 2

def test_zero_effective_width_rejects_everyone_no_pillars():
    r = allocate_first_fit(0.0, SEED_VENDORS, SEED_PILLARS)
    assert r.placements == []
    assert len(r.rejected) == len(SEED_VENDORS)
    assert r.pillar_rects == []
