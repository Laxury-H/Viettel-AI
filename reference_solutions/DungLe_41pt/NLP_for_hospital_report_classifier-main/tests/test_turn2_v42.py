from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v42


ROOT = Path(__file__).resolve().parents[1]


def test_v42_changes_only_seven_exact_candidates_from_v37() -> None:
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v42.repair_exact_hospital_icd_labels(control)

    assert len(changes) == 7
    assert {change["record_id"] for change in changes} == {"6", "11", "66"}
    assert sum(change["after"] == ["I25.1"] for change in changes) == 2
    assert sum(change["after"] == ["N60.2"] for change in changes) == 5

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
    assert changed_candidates == 7


def test_v42_uses_exact_vietnamese_hospital_labels() -> None:
    labels = turn2_v42.EXACT_HOSPITAL_ICD_LABELS
    assert labels["bệnh tim mạch do xơ vữa động mạch"]["after"] == ["I25.1"]
    assert labels["u xơ tuyến vú"]["after"] == ["N60.2"]
