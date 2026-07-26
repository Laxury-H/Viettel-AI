from __future__ import annotations

from pathlib import Path

from scripts.analyze_semantic_context_cohorts import audit
from scripts.analyze_semantic_context_cohorts import template_roots


ROOT = Path(__file__).resolve().parents[1]


def test_template_roots_uses_transitive_near_duplicate_components() -> None:
    roots = template_roots(
        {
            "1": "abcdefghij",
            "2": "abcdefVWXYZ",
            "3": "VWXYZklmnop",
            "4": "unrelated document",
        },
        threshold=0.05,
    )

    assert roots["1"] == roots["2"] == roots["3"] == "1"
    assert roots["4"] == "4"


def test_v45_semantic_audit_tracks_submission_budget() -> None:
    report = audit(
        ROOT / "input",
        ROOT / "submission" / "output.zip",
    )
    cohorts = {item["name"]: item for item in report["cohorts"]}

    assert report["records"] == 100
    assert report["document_templates"] == 69
    assert report["reviewed_occurrences"] == 28
    assert report["candidate_only_occurrences"] == 22

    assert cohorts["unspecified_cerebrovascular_event"]["occurrences"] == 2
    assert cohorts["unspecified_cerebrovascular_event"]["record_ids"] == ["3"]
    assert cohorts["aa_amyloidosis_context_qualifier"]["occurrences"] == 3
    assert cohorts["aa_amyloidosis_context_qualifier"]["template_count"] == 1
