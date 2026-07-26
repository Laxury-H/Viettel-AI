from src.clinical_mentions import turn2_v38


def test_v38_uses_orthogonal_subsystems() -> None:
    assert turn2_v38.turn2_v36.VIETNAM_ICD_STATIC_SPECIFICITY["A09"] == "A09.0"
    assert turn2_v38.turn2_v37.ASSERTION_ORDER == (
        "isNegated",
        "isFamily",
        "isHistorical",
    )
