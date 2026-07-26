from __future__ import annotations

from pathlib import Path

from scripts.analyze_vietnam_label_context_cohorts import audit
from scripts.analyze_vietnam_label_context_cohorts import (
    classify_generic_diabetes,
)


ROOT = Path(__file__).resolve().parents[1]


def entity(text: str, surface: str) -> dict:
    start = text.index(surface)
    return {
        "text": surface,
        "type": "CHẨN_ĐOÁN",
        "position": [start, start + len(surface)],
        "assertions": [],
        "candidates": ["E11.9"],
    }


def test_generic_diabetes_roles_are_not_conflated() -> None:
    chart = "Các bệnh lý mạn tính - đái tháo đường được kiểm soát bằng ăn."
    education = "Yếu tố nguy cơ có thể thay đổi: đái tháo đường, béo phì."
    urinalysis = "Tổng phân tích nước tiểu có đái tháo đườngđái tháo đường."

    assert (
        classify_generic_diabetes(chart, entity(chart, "đái tháo đường"))
        == "clinical_chart_implicit_type"
    )
    assert (
        classify_generic_diabetes(
            education,
            entity(education, "đái tháo đường"),
        )
        == "generic_education"
    )
    assert (
        classify_generic_diabetes(
            urinalysis,
            entity(urinalysis, "đái tháo đường"),
        )
        == "urinalysis_translation_seam"
    )


def test_v45_label_context_audit_preserves_submission_budget() -> None:
    report = audit(ROOT / "input", ROOT / "submission" / "output.zip")

    assert report["records"] == 100
    assert report["document_templates"] == 69
    assert report["generic_diabetes"]["clinical_chart_implicit_type"][
        "occurrences"
    ] == 15
    assert report["generic_diabetes"]["generic_education"][
        "occurrences"
    ] == 4
    assert report["generic_diabetes"]["urinalysis_translation_seam"][
        "occurrences"
    ] == 2
    assert report["generic_osteoporosis"]["occurrences"] == 1
    assert report["unspecified_cerebrovascular_event"]["occurrences"] == 2
    assert report["literal_adjacent_duplicate_pairs"]["occurrences"] == 5
    assert report["reviewed_candidate_only_occurrences"] == 7
    assert report["score_projection"]["v42_optimistic_marginal"] == 0.1161
