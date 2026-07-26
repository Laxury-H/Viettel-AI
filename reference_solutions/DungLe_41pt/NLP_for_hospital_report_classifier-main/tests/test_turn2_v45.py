from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v45


ROOT = Path(__file__).resolve().parents[1]


def test_v45_changes_only_five_exact_candidates_from_v42() -> None:
    control = turn2_v19.load_submission(
        ROOT
        / "submission"
        / "candidate_v42_v37-vietnam-hospital-exact-label-batch.zip"
    )
    output, changes = turn2_v45.repair_exact_vietnam_labels(control)

    assert len(changes) == 5
    assert {change["record_id"] for change in changes} == {
        "2",
        "17",
        "26",
        "30",
        "34",
    }
    assert sum(change["after"] == ["I51.8"] for change in changes) == 1
    assert sum(change["after"] == ["I51.6"] for change in changes) == 2
    assert sum(change["after"] == ["I64"] for change in changes) == 2

    changed_candidates = 0
    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("assertions") == after.get("assertions")
            changed_candidates += (
                before.get("candidates") != after.get("candidates")
            )
    assert changed_candidates == 5


def test_v45_maps_unspecified_stroke_to_i64() -> None:
    target = turn2_v45.EXACT_STROKE_LABEL["đột quỵ"]
    assert target["before"] == ["I63.9"]
    assert target["after"] == ["I64"]
