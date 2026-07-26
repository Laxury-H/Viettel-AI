from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v47


ROOT = Path(__file__).resolve().parents[1]


def test_v47_canonicalization_is_presentation_only() -> None:
    assert turn2_v47.canonical_label("Bệnh béo phì") == "béo phì"
    assert (
        turn2_v47.canonical_label("Bệnh đau nửa đầu [Migraine]")
        == "đau nửa đầu"
    )
    assert (
        turn2_v47.canonical_label(
            "Bệnh trào ngược dạ dày - thực quản"
        )
        == "trào ngược dạ dày thực quản"
    )


def test_v47_frozen_mapping_has_27_cohorts_and_94_occurrences() -> None:
    assert len(turn2_v47.CANONICAL_CATEGORY_LABELS) == 27
    assert sum(turn2_v47.expected_cohort_counts().values()) == 94
    assert turn2_v47.CANONICAL_CATEGORY_LABELS["béo phì"] == {
        "before": "E66.9",
        "after": "E66",
        "expected_count": 12,
    }
    assert turn2_v47.CANONICAL_CATEGORY_LABELS["hẹp ống sống"] == {
        "before": "M48.00",
        "after": "M48.0",
        "expected_count": 4,
    }


def test_v47_changes_only_94_candidates_from_v45() -> None:
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v47.repair_canonical_category_labels(control)

    assert len(changes) == 94
    assert len({change["record_id"] for change in changes}) == 50
    assert (
        turn2_v47.observed_cohort_counts(changes)
        == turn2_v47.expected_cohort_counts()
    )

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
    assert changed_candidates == 94
    assert all(
        change["before"][0].replace(".", "").startswith(
            change["after"][0].replace(".", "")
        )
        for change in changes
    )
