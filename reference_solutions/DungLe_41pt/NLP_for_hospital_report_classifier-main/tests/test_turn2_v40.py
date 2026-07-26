from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v39


ROOT = Path(__file__).resolve().parents[1]


def test_v40_changes_only_six_assertions_from_v37() -> None:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "input").glob("*.txt"), key=lambda p: int(p.stem))
    }
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v39.repair_hybrid_seam_assertions(texts, control)

    assert len(changes) == 6
    assert {change["record_id"] for change in changes} == {"3", "23"}
    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("candidates") == after.get("candidates")
