from scripts.analyze_icd_parent_candidate_structure import category
from scripts.analyze_icd_parent_candidate_structure import canonical_label
from scripts.analyze_icd_parent_candidate_structure import score_projections


def test_icd_category_only_exists_for_dotted_codes() -> None:
    assert category("I50.9") == "I50"
    assert category("M48.00") == "M48"
    assert category("I10") is None


def test_canonical_label_only_removes_presentation_variants() -> None:
    assert canonical_label("Bệnh béo phì") == "béo phì"
    assert canonical_label("Bệnh đau nửa đầu [Migraine]") == "đau nửa đầu"
    assert (
        canonical_label("Bệnh trào ngược dạ dày - thực quản")
        == "trào ngược dạ dày thực quản"
    )


def test_parent_label_projection_keeps_replacement_and_augmentation_separate() -> None:
    projections = score_projections(47)

    assert projections["v34_v35_code_system_mean"]["replacement"] == 0.4679
    assert (
        projections["v34_v35_code_system_mean"][
            "two_code_augmentation_max_half_credit"
        ]
        == 0.234
    )
    assert projections["v42_exact_label_optimistic"]["replacement"] == 0.7795
    assert (
        projections["v42_exact_label_optimistic"][
            "two_code_augmentation_max_half_credit"
        ]
        == 0.3898
    )
