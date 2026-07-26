from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v41


ROOT = Path(__file__).resolve().parents[1]


def test_v41_changes_only_two_exact_candidates_from_v37() -> None:
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v41.repair_exact_vietnam_icd_labels(control)

    assert len(changes) == 2
    assert {change["record_id"] for change in changes} == {"6", "11"}
    assert {tuple(change["before"]) for change in changes} == {("I70.90",)}
    assert {tuple(change["after"]) for change in changes} == {("I25.1",)}

    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("assertions") == after.get("assertions")


def test_v41_targets_exact_official_vietnamese_label() -> None:
    assert set(turn2_v41.EXACT_VIETNAM_ICD_LABELS) == {
        "bệnh tim mạch do xơ vữa động mạch"
    }
    target = turn2_v41.EXACT_VIETNAM_ICD_LABELS[
        "bệnh tim mạch do xơ vữa động mạch"
    ]
    assert target["before"] == ["I70.90"]
    assert target["after"] == ["I25.1"]
