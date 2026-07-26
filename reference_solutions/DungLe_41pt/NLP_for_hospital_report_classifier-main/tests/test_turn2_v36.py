from copy import deepcopy

from src.clinical_mentions import turn2_v36


def test_static_specificity_mapping_is_small_and_reviewed() -> None:
    mapping = turn2_v36.VIETNAM_ICD_STATIC_SPECIFICITY
    assert len(mapping) == 7
    assert mapping["S06.4"] == "S06.40"
    assert mapping["M10.9"] == "M10.90"
    assert mapping["M81.0"] == "M81.99"
    assert mapping["I70.1"] == "I70.10"
    assert mapping["A09"] == "A09.0"


def test_osteomyelitis_uses_record_context() -> None:
    assert turn2_v36.OSTEOMYELITIS_BY_RECORD == {
        "59": "M86.99",
        "85": "M86.97",
        "92": "M86.69",
        "99": "M86.69",
    }


def test_apply_specificity_changes_candidates_only() -> None:
    source = {
        "6": [
            {
                "text": "tụ máu ngoài màng cứng",
                "type": "CHẨN_ĐOÁN",
                "candidates": ["S06.4"],
                "assertions": ["isHistorical"],
                "position": [1, 24],
            }
        ],
        "85": [
            {
                "text": "viêm xương tủy",
                "type": "CHẨN_ĐOÁN",
                "candidates": ["M86.9"],
                "assertions": ["isNegated"],
                "position": [10, 24],
            }
        ],
    }
    before = deepcopy(source)
    output, changes = turn2_v36.apply_vietnam_specificity(source)

    assert output["6"][0]["candidates"] == ["S06.40"]
    assert output["85"][0]["candidates"] == ["M86.97"]
    assert output["6"][0]["text"] == before["6"][0]["text"]
    assert output["6"][0]["position"] == before["6"][0]["position"]
    assert output["6"][0]["assertions"] == before["6"][0]["assertions"]
    assert len(changes) == 2
