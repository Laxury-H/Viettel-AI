from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v54


ROOT = Path(__file__).resolve().parents[1]


def load_inputs() -> tuple[dict[str, str], dict[str, list[dict]]]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(
            (ROOT / "input").glob("*.txt"),
            key=lambda path: int(path.stem),
        )
    }
    control = turn2_v19.load_submission(
        ROOT
        / "submission"
        / "candidate_v53_v51-explicit-medication-section-temporality.zip"
    )
    return texts, control


def test_v54_changes_exactly_eight_reviewed_mentions() -> None:
    texts, control = load_inputs()
    output, changes = turn2_v54.complete_explicit_past_assertions(
        texts,
        control,
    )

    assert {
        (
            change["record_id"],
            *change["position"],
            change["text"],
        )
        for change in changes
    } == turn2_v54.EXPECTED_TARGETS
    assert len(changes) == 8
    assert sum(change["record_id"] == "4" for change in changes) == 6
    assert sum(change["record_id"] == "69" for change in changes) == 2

    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("candidates") == after.get("candidates")


def test_v54_keeps_negation_when_adding_historical() -> None:
    texts, control = load_inputs()
    output, _ = turn2_v54.complete_explicit_past_assertions(texts, control)

    targets = {
        tuple(entity["position"]): entity
        for entity in output["69"]
        if tuple(entity["position"]) in {(555, 563), (595, 607)}
    }
    assert targets[(555, 563)]["assertions"] == [
        "isNegated",
        "isHistorical",
    ]
    assert targets[(595, 607)]["assertions"] == [
        "isNegated",
        "isHistorical",
    ]


def test_v54_preserves_non_past_hpi_mentions() -> None:
    texts, control = load_inputs()
    output, _ = turn2_v54.complete_explicit_past_assertions(texts, control)

    current_blood_vomit = next(
        entity
        for entity in output["4"]
        if entity["position"] == [726, 736]
    )
    assert current_blood_vomit["text"] == "Nôn ra máu"
    assert current_blood_vomit["assertions"] == []
