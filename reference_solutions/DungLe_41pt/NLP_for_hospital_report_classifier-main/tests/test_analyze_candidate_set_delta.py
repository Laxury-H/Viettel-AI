from __future__ import annotations

from pathlib import Path

from scripts.analyze_candidate_set_delta import analyze


ROOT = Path(__file__).resolve().parents[1]


def test_v49_occurrences_collapse_to_four_record_set_changes() -> None:
    report = analyze(
        ROOT / "submission" / "output.zip",
        ROOT
        / "submission"
        / "candidate_v49_v45-vietnam-source-semantic-cross-family.zip",
    )
    assert report["entity_candidate_changes"] == 5
    assert report["record_candidate_set_changes"] == 4
    assert report["record_candidate_codes_removed"] == 1
    assert report["record_candidate_codes_added"] == 4


def test_v42_seven_occurrences_form_three_record_substitutions() -> None:
    report = analyze(
        ROOT
        / "submission"
        / "candidate_v37_v35-vietnam-document-archetype-assertion-probe.zip",
        ROOT
        / "submission"
        / "candidate_v42_v37-vietnam-hospital-exact-label-batch.zip",
    )
    assert report["entity_candidate_changes"] == 7
    assert report["record_candidate_set_changes"] == 3
    assert report["record_candidate_codes_removed"] == 3
    assert report["record_candidate_codes_added"] == 3
