from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v44


ROOT = Path(__file__).resolve().parents[1]


def test_v44_changes_only_three_exact_i51_candidates_from_v42() -> None:
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v44.repair_exact_vietnam_i51_labels(control)

    assert len(changes) == 3
    assert {change["record_id"] for change in changes} == {"2", "26", "30"}
    assert sum(change["after"] == ["I51.8"] for change in changes) == 1
    assert sum(change["after"] == ["I51.6"] for change in changes) == 2

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
    assert changed_candidates == 3


def test_v44_encodes_the_vietnamese_i51_label_distinctions() -> None:
    labels = turn2_v44.EXACT_VIETNAM_I51_LABELS
    assert labels["viêm tim"]["before"] == ["I51.4"]
    assert labels["viêm tim"]["after"] == ["I51.8"]
    assert labels["bệnh tim mạch"]["before"] == ["I51.9"]
    assert labels["bệnh tim mạch"]["after"] == ["I51.6"]
