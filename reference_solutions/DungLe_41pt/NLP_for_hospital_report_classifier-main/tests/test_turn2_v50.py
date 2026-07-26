from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v50


ROOT = Path(__file__).resolve().parents[1]


def test_v50_isolates_two_record3_stroke_synonyms() -> None:
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v50.repair_unspecified_stroke_synonym(control)

    assert len(changes) == 2
    assert {change["record_id"] for change in changes} == {"3"}
    assert all(change["text"].casefold() == "tai biến mạch máu não" for change in changes)
    assert all(change["before"] == ["I63.9"] for change in changes)
    assert all(change["after"] == ["I64"] for change in changes)

    changed_candidates = 0
    for record_id, before_entities in control.items():
        after_entities = output[record_id]
        assert len(after_entities) == len(before_entities)
        for before, after in zip(before_entities, after_entities):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before["assertions"] == after["assertions"]
            assert len(before.get("candidates", [])) == len(
                after.get("candidates", [])
            )
            changed_candidates += (
                before.get("candidates") != after.get("candidates")
            )
    assert changed_candidates == 2


def test_v50_does_not_change_existing_dot_quy_entities() -> None:
    control = {
        "1": [
            {
                "text": "đột quỵ",
                "type": "CHẨN_ĐOÁN",
                "assertions": [],
                "position": [0, 7],
                "candidates": ["I64"],
            }
        ]
    }
    output, changes = turn2_v50.repair_unspecified_stroke_synonym(control)
    assert changes == []
    assert output == control
