from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v43


ROOT = Path(__file__).resolve().parents[1]


def test_v43_completes_only_three_exact_official_labels() -> None:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "input").glob("*.txt"), key=lambda p: int(p.stem))
    }
    control = turn2_v19.load_submission(
        ROOT
        / "submission"
        / "candidate_v42_v37-vietnam-hospital-exact-label-batch.zip"
    )
    output, changes = turn2_v43.complete_exact_icd_label_boundaries(
        texts, control
    )

    assert len(changes) == 3
    assert {change["record_id"] for change in changes} == {"26", "39", "47"}
    assert sum(
        change["after"]["candidates"] == ["F31.8"] for change in changes
    ) == 1
    assert sum(
        change["after"]["candidates"] == ["J44.9"] for change in changes
    ) == 2

    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["type"] == after["type"]
            assert before.get("assertions") == after.get("assertions")
