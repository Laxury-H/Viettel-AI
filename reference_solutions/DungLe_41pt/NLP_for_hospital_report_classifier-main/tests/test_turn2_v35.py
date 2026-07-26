from src.clinical_mentions import turn2_v35


def test_final_mapping_has_reviewed_nonoverlapping_layers() -> None:
    assert len(turn2_v35.VIETNAM_ICD_EXPANSION) == 42
    assert len(turn2_v35.VIETNAM_ICD_FULL) == 62
    assert not (
        set(turn2_v35.VIETNAM_ICD_EXPANSION)
        & set(turn2_v35.turn2_v34.VIETNAM_ICD_ANCHOR)
    )


def test_ambiguous_combined_hepatitis_codes_are_excluded() -> None:
    assert "B19.1" not in turn2_v35.VIETNAM_ICD_FULL
    assert "B19.2" not in turn2_v35.VIETNAM_ICD_FULL


def test_vietnam_specific_semantic_crosswalks() -> None:
    mapping = turn2_v35.VIETNAM_ICD_FULL
    assert mapping["D75.A"] == "D55.0"
    assert mapping["I82.409"] == "I80.2"
    assert mapping["K72.90"] == "K74.6"
    assert mapping["M1A.9XX1"] == "M10.90"
    assert mapping["T14.8XXA"] == "T14.20"


def test_select_icd_mapping_modes() -> None:
    assert turn2_v35.select_icd_mapping("drop") == {}
    assert len(turn2_v35.select_icd_mapping("anchor")) == 20
    assert len(turn2_v35.select_icd_mapping("full")) == 62
