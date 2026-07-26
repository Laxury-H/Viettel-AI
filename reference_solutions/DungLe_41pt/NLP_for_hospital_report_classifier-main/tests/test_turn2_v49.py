from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v49


ROOT = Path(__file__).resolve().parents[1]


def load_inputs() -> tuple[dict[str, str], dict[str, list[dict]]]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(
            (ROOT / "input").glob("*.txt"),
            key=lambda path: int(path.stem),
        )
    }
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    return texts, control


def test_v49_changes_only_five_existing_candidates() -> None:
    texts, control = load_inputs()
    output, changes = turn2_v49.repair_source_semantic_candidates(
        texts, control
    )

    assert len(changes) == 5
    assert turn2_v49.observed_counts(changes) == turn2_v49.EXPECTED_COUNTS
    assert {change["record_id"] for change in changes} == {
        "3",
        "21",
        "32",
        "79",
    }

    changed_candidates = 0
    for record_id, before_entities in control.items():
        after_entities = output[record_id]
        assert len(after_entities) == len(before_entities)
        for before, after in zip(before_entities, after_entities):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before["assertions"] == after["assertions"]
            changed_candidates += (
                before.get("candidates") != after.get("candidates")
            )
    assert changed_candidates == 5


def test_v49_uses_reviewed_cross_family_targets() -> None:
    texts, control = load_inputs()
    _, changes = turn2_v49.repair_source_semantic_candidates(texts, control)

    stroke = [
        change
        for change in changes
        if change["cohort"] == "unspecified_cerebrovascular_event"
    ]
    amyloidosis = [
        change
        for change in changes
        if change["cohort"] == "aa_secondary_systemic_amyloidosis"
    ]
    assert len(stroke) == 2
    assert all(change["before"] == ["I63.9"] for change in stroke)
    assert all(change["after"] == ["I64"] for change in stroke)
    assert len(amyloidosis) == 3
    assert all(change["before"] == ["E85.9"] for change in amyloidosis)
    assert all(change["after"] == ["E85.3"] for change in amyloidosis)


def test_v49_aa_suffix_gate_is_strict() -> None:
    assert turn2_v49.has_aa_amyloidosis_suffix(" tự miễn dịch")
    assert turn2_v49.has_aa_amyloidosis_suffix(" - TỰ MIỄN DỊCH")
    assert not turn2_v49.has_aa_amyloidosis_suffix(" chuỗi nhẹ")
    assert not turn2_v49.has_aa_amyloidosis_suffix(" di truyền")
