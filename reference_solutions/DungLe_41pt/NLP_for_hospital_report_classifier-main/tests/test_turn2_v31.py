from src.clinical_mentions import turn2_v31


def symptom(text: str, start: int, assertions: list[str] | None = None) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": assertions or [],
        "position": [start, start + len(text)],
    }


def test_semantic_boundary_completes_anatomical_location() -> None:
    text = "Bệnh nhân vẫn còn đau đầu vùng thái dương phải."
    start = text.index("đau đầu")
    expansions = turn2_v31.derive_semantic_boundary_expansions(
        {"1": text},
        {"1": [symptom("đau đầu", start)]},
    )
    assert len(expansions) == 1
    assert expansions[0].after_text == "đau đầu vùng thái dương phải"


def test_semantic_boundary_excludes_leading_change_modifier() -> None:
    text = "Bệnh nhân tăng đánh trống ngực."
    start = text.index("đánh trống ngực")
    expansions = turn2_v31.derive_semantic_boundary_expansions(
        {"1": text},
        {"1": [symptom("đánh trống ngực", start)]},
    )
    assert expansions == []


def test_epistemic_question_is_not_symptom_negation() -> None:
    text = "Không biết là tình trạng đi cầu phân sống đã lâu chưa?"
    start = text.index("đi cầu phân sống")
    addition = turn2_v31.turn2_v27.RepeatedLineAddition(
        record_id="1",
        start=start,
        end=start + len("đi cầu phân sống"),
        entity_type="TRIỆU_CHỨNG",
        surface="đi cầu phân sống",
        source_record_ids=(),
    )
    output, changes = turn2_v31.apply_contextual_recall_additions(
        {"1": text},
        {"1": []},
        [addition],
    )
    assert output["1"][0]["assertions"] == []
    assert changes[0]["epistemic_negation_override"] is True


def test_true_negation_is_preserved_for_contextual_recall() -> None:
    text = "Bé không có đi cầu phân sống."
    start = text.index("đi cầu phân sống")
    addition = turn2_v31.turn2_v27.RepeatedLineAddition(
        record_id="1",
        start=start,
        end=start + len("đi cầu phân sống"),
        entity_type="TRIỆU_CHỨNG",
        surface="đi cầu phân sống",
        source_record_ids=(),
    )
    output, changes = turn2_v31.apply_contextual_recall_additions(
        {"1": text},
        {"1": []},
        [addition],
    )
    assert output["1"][0]["assertions"] == ["isNegated"]
    assert changes[0]["epistemic_negation_override"] is False
