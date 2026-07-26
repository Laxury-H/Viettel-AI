from src.clinical_mentions.turn2_v17 import (
    eligible_consensus_spans,
    has_direct_causal_negation,
    has_leading_change_modifier,
)


def span(
    start: int,
    end: int,
    confidence: float,
    entity_type: str = "TRIỆU_CHỨNG",
) -> dict:
    return {
        "start": start,
        "end": end,
        "type": entity_type,
        "confidence": confidence,
    }


def test_consensus_requires_exact_span_type_and_calibrated_thresholds() -> None:
    text = "đau lưng và khó thở"
    first = [
        span(0, 8, 0.99),
        span(12, 19, 0.99),
    ]
    second = [
        span(0, 8, 0.988),
        span(12, 18, 0.999),
    ]
    assert eligible_consensus_spans(
        text,
        first,
        second,
        second_threshold=0.9875,
    ) == [
        {
            "start": 0,
            "end": 8,
            "type": "TRIỆU_CHỨNG",
            "first_confidence": 0.99,
            "second_confidence": 0.988,
        }
    ]


def test_consensus_rejects_generic_anatomy_surface() -> None:
    assert (
        eligible_consensus_spans(
            "bụng",
            [span(0, 4, 0.999)],
            [span(0, 4, 0.999)],
            second_threshold=0.9875,
        )
        == []
    )


def test_direct_causal_negation_is_concept_local() -> None:
    text = "Thuốc thế hệ mới không gây buồn ngủ."
    assert has_direct_causal_negation(text, text.index("buồn ngủ"))
    assert not has_direct_causal_negation("Không dùng thuốc vì buồn ngủ", 20)


def test_change_modifier_is_not_absorbed_into_existing_symptom() -> None:
    text = "T\u0103ng \u0111\u00e1nh tr\u1ed1ng ng\u1ef1c"
    existing_start = text.index("\u0111\u00e1nh")
    assert has_leading_change_modifier(text, 0, existing_start)
    assert not has_leading_change_modifier(text, existing_start, existing_start)
