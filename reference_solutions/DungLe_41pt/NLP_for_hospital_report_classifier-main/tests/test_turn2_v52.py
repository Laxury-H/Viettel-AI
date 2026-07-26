from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v52


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


def test_v52_removes_only_eight_second_duplicate_tokens() -> None:
    texts, control = load_inputs()
    output, changes = turn2_v52.prune_literal_duplicate_symptoms(
        texts,
        control,
    )

    assert len(changes) == 8
    assert {change["record_id"] for change in changes} == {
        "39",
        "47",
        "61",
        "62",
        "77",
    }
    assert {
        (change["record_id"], *change["position"]) for change in changes
    } == {
        ("39", 1548, 1551),
        ("47", 1130, 1133),
        ("47", 1458, 1461),
        ("39", 1031, 1038),
        ("47", 1383, 1390),
        ("61", 803, 810),
        ("62", 436, 443),
        ("77", 499, 502),
    }
    assert [turn2_v52.normalize(change["text"]) for change in changes].count(
        "phù"
    ) == 3
    assert [turn2_v52.normalize(change["text"]) for change in changes].count(
        "đau"
    ) == 1
    assert [turn2_v52.normalize(change["text"]) for change in changes].count(
        "mệt mỏi"
    ) == 4

    for record_id in control:
        expected_delta = -sum(
            change["record_id"] == record_id for change in changes
        )
        assert (
            len(output[record_id]) - len(control[record_id])
            == expected_delta
        )
        for entity in output[record_id]:
            assert entity in control[record_id]


def test_v52_retains_first_token_and_requires_whitespace_gap() -> None:
    texts, control = load_inputs()
    output, _ = turn2_v52.prune_literal_duplicate_symptoms(texts, control)

    retained = {
        (record_id, *entity["position"])
        for record_id, entities in output.items()
        for entity in entities
    }
    assert {
        ("39", 1544, 1547),
        ("47", 1126, 1129),
        ("47", 1454, 1457),
        ("39", 1021, 1028),
        ("47", 1373, 1380),
        ("61", 793, 800),
        ("62", 422, 429),
        ("77", 495, 498),
    } <= retained

    no_gap_entities = [
        {
            "text": "đau",
            "type": "TRIỆU_CHỨNG",
            "assertions": [],
            "position": [0, 3],
        },
        {
            "text": "đau",
            "type": "TRIỆU_CHỨNG",
            "assertions": [],
            "position": [3, 6],
        },
    ]
    assert turn2_v52.duplicate_second_keys(
        "đauđau",
        no_gap_entities,
    ) == set()
