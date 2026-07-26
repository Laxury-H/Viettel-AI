from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v51


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
        / "candidate_v45_v42-vietnam-exact-label-cross-family.zip"
    )
    return texts, control


def test_v51_removes_only_two_record38_seam_entities() -> None:
    texts, control = load_inputs()
    output, changes = (
        turn2_v51.prune_urinalysis_translation_false_positives(
            texts,
            control,
        )
    )

    assert len(changes) == 2
    assert {change["record_id"] for change in changes} == {"38"}
    assert {tuple(change["position"]) for change in changes} == {
        (1733, 1747),
        (1747, 1761),
    }
    assert all(change["candidates"] == ["E11.9"] for change in changes)

    for record_id in control:
        expected_delta = -2 if record_id == "38" else 0
        assert (
            len(output[record_id]) - len(control[record_id])
            == expected_delta
        )
        for entity in output[record_id]:
            assert entity in control[record_id]


def test_v51_retains_valid_type2_diabetes_and_rejects_plain_context() -> None:
    texts, control = load_inputs()
    output, _ = turn2_v51.prune_urinalysis_translation_false_positives(
        texts,
        control,
    )

    valid = [
        entity
        for entity in output["38"]
        if turn2_v51.normalize(entity["text"]) == "đái tháo đường típ 2"
    ]
    assert len(valid) == 1
    assert valid[0]["candidates"] == ["E11.9"]
    assert valid[0]["assertions"] == ["isHistorical"]

    ordinary = {
        "text": "đái tháo đường",
        "type": "CHẨN_ĐOÁN",
        "assertions": [],
        "position": [0, 14],
        "candidates": ["E11.9"],
    }
    assert not turn2_v51.is_urinalysis_translation_false_positive(
        "đái tháo đường đang điều trị",
        ordinary,
    )
