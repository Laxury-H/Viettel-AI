from src.clinical_mentions import turn2_v19


def entity(text: str, start: int, end: int) -> dict:
    return {
        "text": text[start:end],
        "type": turn2_v19.SYMPTOM_TYPE,
        "position": [start, end],
        "assertions": [],
    }


def span(start: int, end: int, confidence: float) -> dict:
    return {
        "start": start,
        "end": end,
        "type": turn2_v19.SYMPTOM_TYPE,
        "confidence": confidence,
    }


def test_additive_profile_only_adds_non_overlapping_consensus() -> None:
    text = "Bệnh nhân đau đầu và mệt."
    existing = [entity(text, 10, 17)]
    output, stats = turn2_v19.refine_entities(
        text,
        existing,
        [span(21, 24, 0.99)],
        [span(21, 24, 0.92)],
        profile="xlmr-additive-90",
    )
    assert [(item["text"], item["position"]) for item in output] == [
        ("đau đầu", [10, 17]),
        ("mệt", [21, 24]),
    ]
    assert stats["entities_added"] == 1
    assert stats["boundaries_replaced"] == 0


def test_safe_boundary_profile_expands_one_symptom() -> None:
    text = "Bệnh nhân đau đầu kéo dài."
    existing = [entity(text, 10, 17)]
    output, stats = turn2_v19.refine_entities(
        text,
        existing,
        [span(10, 25, 0.99)],
        [span(10, 25, 0.95)],
        profile="xlmr-safe-94",
    )
    assert [(item["text"], item["position"]) for item in output] == [
        ("đau đầu kéo dài", [10, 25])
    ]
    assert stats["entities_added"] == 0
    assert stats["boundaries_replaced"] == 1


def test_safe_boundary_rejects_cross_sentence_span() -> None:
    text = "Bệnh nhân chảy nước mũi.Nhiều người bệnh."
    existing = [entity(text, 10, 23)]
    output, stats = turn2_v19.refine_entities(
        text,
        existing,
        [span(10, 29, 0.99)],
        [span(10, 29, 0.96)],
        profile="xlmr-safe-94",
    )
    assert output == existing
    assert stats["boundaries_replaced"] == 0
    assert stats["proposals_rejected"] == 1


def test_addition_does_not_overlap_another_entity_type() -> None:
    text = "Kết quả tê bì tay."
    existing = [
        {
            "text": "tê bì tay",
            "type": "KẾT_QUẢ_XÉT_NGHIỆM",
            "position": [9, 18],
            "assertions": [],
        }
    ]
    output, stats = turn2_v19.refine_entities(
        text,
        existing,
        [span(9, 14, 0.99)],
        [span(9, 14, 0.92)],
        profile="xlmr-additive-90",
    )
    assert output == existing
    assert stats["entities_added"] == 0


def test_addition_rejects_inferred_assertion() -> None:
    text = "Không ghi nhận mệt."
    output, stats = turn2_v19.refine_entities(
        text,
        [],
        [span(15, 18, 0.99)],
        [span(15, 18, 0.92)],
        profile="xlmr-additive-90",
    )
    assert output == []
    assert stats["entities_added"] == 0
    assert stats["proposals_rejected"] == 1
