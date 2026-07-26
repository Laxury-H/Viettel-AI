from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v53


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
        / "candidate_v51_v45-urinalysis-translation-pruning.zip"
    )
    return texts, control


def test_v53_changes_only_two_reviewed_medication_assertions() -> None:
    texts, control = load_inputs()
    output, changes = (
        turn2_v53.complete_historical_medication_assertions(texts, control)
    )

    assert {
        (
            change["record_id"],
            *change["position"],
            change["text"],
        )
        for change in changes
    } == {
        ("57", 224, 233, "Torsemide"),
        ("92", 321, 328, "bactrim"),
    }
    assert all(change["before_assertions"] == [] for change in changes)
    assert all(
        change["after_assertions"] == ["isHistorical"]
        for change in changes
    )

    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("candidates") == after.get("candidates")


def test_v53_does_not_propagate_to_medication_indication() -> None:
    text = (
        "Thuốc trước khi nhập viện:\n"
        "guaifenesin ml po q6h:prn điều trị ho\n"
        "2. Bệnh sử hiện tại\n"
    )
    drug_start = text.index("guaifenesin")
    symptom_start = text.index("ho")
    source = {
        "1": [
            {
                "text": "guaifenesin ml po q6h:prn",
                "type": "THUỐC",
                "candidates": ["392085"],
                "assertions": [],
                "position": [
                    drug_start,
                    drug_start + len("guaifenesin ml po q6h:prn"),
                ],
            },
            {
                "text": "ho",
                "type": "TRIỆU_CHỨNG",
                "assertions": [],
                "position": [symptom_start, symptom_start + 2],
            },
        ]
    }

    output, changes = turn2_v53.complete_historical_medication_assertions(
        {"1": text},
        source,
    )

    assert len(changes) == 1
    assert output["1"][0]["assertions"] == ["isHistorical"]
    assert output["1"][1]["assertions"] == []


def test_v53_stops_at_next_strong_section() -> None:
    text = (
        "Thuốc đã dùng trước đây\n"
        "aspirin 81 mg\n"
        "2. Bệnh sử hiện tại\n"
        "đang dùng metoprolol\n"
    )
    aspirin_start = text.index("aspirin")
    metoprolol_start = text.index("metoprolol")
    source = {
        "1": [
            {
                "text": "aspirin 81 mg",
                "type": "THUỐC",
                "candidates": ["243670"],
                "assertions": [],
                "position": [aspirin_start, aspirin_start + 13],
            },
            {
                "text": "metoprolol",
                "type": "THUỐC",
                "candidates": ["6918"],
                "assertions": [],
                "position": [metoprolol_start, metoprolol_start + 10],
            },
        ]
    }

    output, changes = turn2_v53.complete_historical_medication_assertions(
        {"1": text},
        source,
    )

    assert len(changes) == 1
    assert output["1"][0]["assertions"] == ["isHistorical"]
    assert output["1"][1]["assertions"] == []
