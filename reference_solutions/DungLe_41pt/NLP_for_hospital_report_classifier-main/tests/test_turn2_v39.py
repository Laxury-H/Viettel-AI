from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v39


ROOT = Path(__file__).resolve().parents[1]


def load_fixture() -> tuple[dict[str, str], dict[str, list[dict]]]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "input").glob("*.txt"), key=lambda p: int(p.stem))
    }
    records = turn2_v19.load_submission(
        ROOT
        / "submission"
        / "candidate_v35_v30-vietnam-icd-full-final.zip"
    )
    return texts, records


def test_hybrid_seam_repairs_are_isolated() -> None:
    texts, records = load_fixture()
    output, changes = turn2_v39.repair_hybrid_seam_assertions(texts, records)

    assert len(changes) == 6
    assert {change["record_id"] for change in changes} == {"3", "23"}
    assert [change["reason"] for change in changes].count("current_question") == 2
    assert [change["reason"] for change in changes].count("generic_education") == 2
    assert [change["reason"] for change in changes].count("generic_advice") == 2

    for record_id in records:
        assert len(output[record_id]) == len(records[record_id])
        for before, after in zip(records[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("candidates") == after.get("candidates")


def test_hybrid_seam_repairs_only_remove_historical() -> None:
    texts, records = load_fixture()
    _, changes = turn2_v39.repair_hybrid_seam_assertions(texts, records)

    for change in changes:
        assert "isHistorical" in change["before"]
        assert "isHistorical" not in change["after"]
        assert set(change["before"]) - {"isHistorical"} == set(change["after"])
