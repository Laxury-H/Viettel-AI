from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v48


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


def test_v48_adds_only_frozen_exact_diagnosis_recall() -> None:
    texts, control = load_inputs()
    output, changes = turn2_v48.apply_exact_diagnosis_recall(texts, control)

    assert len(changes) == turn2_v48.EXPECTED_ADDITIONS
    assert turn2_v48.observed_counts(changes) == turn2_v48.expected_counts()
    assert {change["record_id"] for change in changes} == {
        "3",
        "17",
        "18",
        "41",
        "49",
        "60",
        "65",
        "92",
    }

    for record_id, before_entities in control.items():
        after_entities = output[record_id]
        for before in before_entities:
            assert before in after_entities
        assert len(after_entities) - len(before_entities) == sum(
            change["record_id"] == record_id for change in changes
        )


def test_v48_assigns_reviewed_leaf_codes_and_true_negation() -> None:
    texts, control = load_inputs()
    _, changes = turn2_v48.apply_exact_diagnosis_recall(texts, control)

    by_surface: dict[str, list[dict]] = {}
    for change in changes:
        by_surface.setdefault(
            turn2_v48.normalize_surface(change["text"]),
            [],
        ).append(change)

    assert {
        change["candidates"][0] for change in by_surface["trứng cá"]
    } == {"L70.9"}
    assert {
        change["candidates"][0]
        for change in by_surface["rụng tóc toàn bộ"]
    } == {"L63.1"}
    assert {
        change["candidates"][0] for change in by_surface["mày đay"]
    } == {"L50.9"}
    assert {
        change["candidates"][0] for change in by_surface["bạch biến"]
    } == {"L80"}
    assert by_surface["viêm túi mật"][0]["assertions"] == ["isNegated"]
