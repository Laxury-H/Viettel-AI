from src.clinical_mentions import turn2_v26


def symptom(text: str, start: int) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": [],
        "position": [start, start + len(text)],
    }


def test_derives_strict_expansion_but_rejects_contraction() -> None:
    base = {
        "1": [
            symptom("đau bụng", 0),
            symptom("Nôn mửa", 30),
        ]
    }
    candidate = {
        "1": [
            symptom("đau bụng râm ran", 0),
            symptom("Nôn", 30),
        ]
    }
    expansions = turn2_v26.derive_stable_expansions(base, candidate)
    assert len(expansions) == 1
    assert expansions[0].after_text == "đau bụng râm ran"


def test_applies_boundary_only_and_preserves_assertions() -> None:
    control_entity = symptom("đau", 5)
    control_entity["assertions"] = ["isHistorical"]
    expansion = turn2_v26.BoundaryExpansion(
        record_id="1",
        before_key=(5, 8, "TRIỆU_CHỨNG"),
        after_text="đau các khớp",
        after_position=(5, 17),
    )
    output, changes = turn2_v26.apply_expansions(
        {"1": [control_entity]},
        [expansion],
    )
    assert output["1"] == [
        {
            "text": "đau các khớp",
            "type": "TRIỆU_CHỨNG",
            "assertions": ["isHistorical"],
            "position": [5, 17],
        }
    ]
    assert len(changes) == 1
