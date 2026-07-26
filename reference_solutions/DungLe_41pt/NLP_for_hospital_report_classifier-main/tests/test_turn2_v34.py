from src.clinical_mentions import turn2_v34


def entity(
    surface: str,
    entity_type: str,
    candidates: list[str],
) -> dict:
    return {
        "text": surface,
        "type": entity_type,
        "assertions": [],
        "position": [0, len(surface)],
        "candidates": candidates,
    }


def test_official_vietnam_icd_replaces_diagnosis_code() -> None:
    records = {
        "1": [
            entity("Thiếu men G6PD", "CHẨN_ĐOÁN", ["D75.A"]),
            entity("viêm dạ dày", "CHẨN_ĐOÁN", ["K29.70"]),
        ]
    }
    output, changes = turn2_v34.apply_vietnam_icd_anchor(records)
    assert output["1"][0]["candidates"] == ["D55.0"]
    assert output["1"][1]["candidates"] == ["K29.7"]
    assert len(changes) == 2


def test_rxnorm_and_unmapped_icd_are_unchanged() -> None:
    records = {
        "1": [
            entity("metoprolol", "THUỐC", ["866924"]),
            entity("tăng huyết áp", "CHẨN_ĐOÁN", ["I10"]),
        ]
    }
    output, changes = turn2_v34.apply_vietnam_icd_anchor(records)
    assert output == records
    assert changes == []


def test_mapped_code_only_applies_to_diagnosis_type() -> None:
    records = {"1": [entity("thuốc giả", "THUỐC", ["K29.70"])]}
    output, changes = turn2_v34.apply_vietnam_icd_anchor(records)
    assert output["1"][0]["candidates"] == ["K29.70"]
    assert changes == []


def test_anchor_targets_are_unique_and_nonempty() -> None:
    mapping = turn2_v34.VIETNAM_ICD_ANCHOR
    assert len(mapping) == 20
    assert len(set(mapping.values())) == 20
    assert all(source != target for source, target in mapping.items())
