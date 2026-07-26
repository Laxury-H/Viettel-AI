from __future__ import annotations

from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v46


ROOT = Path(__file__).resolve().parents[1]


def test_v46_changes_only_six_contextual_candidates_from_v45() -> None:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "input").glob("*.txt"), key=lambda p: int(p.stem))
    }
    control = turn2_v19.load_submission(ROOT / "submission" / "output.zip")
    output, changes = turn2_v46.repair_intracranial_pressure_translation(
        texts, control
    )

    assert len(changes) == 6
    assert {change["record_id"] for change in changes} == {
        "23",
        "27",
        "45",
        "50",
    }
    assert sum(
        change["context_signature"] == "head_ct_and_papilloedema"
        for change in changes
    ) == 3
    assert sum(
        change["context_signature"] == "neonatal_csf_drainage"
        for change in changes
    ) == 3
    assert all(change["before"] == ["H40.9"] for change in changes)
    assert all(change["after"] == ["G93.2"] for change in changes)

    changed_candidates = 0
    for record_id in control:
        assert len(output[record_id]) == len(control[record_id])
        for before, after in zip(control[record_id], output[record_id]):
            assert before["text"] == after["text"]
            assert before["type"] == after["type"]
            assert before["position"] == after["position"]
            assert before.get("assertions") == after.get("assertions")
            changed_candidates += (
                before.get("candidates") != after.get("candidates")
            )
    assert changed_candidates == 6


def test_v46_requires_neurological_context() -> None:
    assert turn2_v46.has_intracranial_context(
        "Phù gai thị; chụp cắt lớp vi tính (ct) đầu"
    )
    assert turn2_v46.has_intracranial_context(
        "thời kỳ sơ sinh; hệ thống dẫn lưu được chỉnh sửa"
    )
    assert not turn2_v46.has_intracranial_context(
        "khám mắt định kỳ vì tăng nhãn áp"
    )
