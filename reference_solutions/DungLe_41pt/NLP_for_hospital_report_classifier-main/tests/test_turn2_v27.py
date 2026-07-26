from src.clinical_mentions import turn2_v26, turn2_v27


def expansion(
    text: str,
    *,
    record_id: str = "1",
    start: int = 0,
    end: int | None = None,
) -> turn2_v26.BoundaryExpansion:
    end = len(text) if end is None else end
    return turn2_v26.BoundaryExpansion(
        record_id=record_id,
        before_key=(start, min(start + 4, end), "TRIỆU_CHỨNG"),
        after_text=text,
        after_position=(start, end),
    )


def test_semantic_filter_rejects_modifier_and_compound_boundaries() -> None:
    texts = {"1": "Tăng đánh trống ngực"}
    assert not turn2_v27.keep_semantic_expansion(
        expansion("Tăng đánh trống ngực"),
        texts,
    )
    texts["1"] = "đau bụng/khó chịu vùng bụng"
    assert not turn2_v27.keep_semantic_expansion(
        expansion("đau bụng/khó chịu vùng bụng"),
        texts,
    )


def test_semantic_filter_rejects_span_cut_before_laterality() -> None:
    texts = {"1": "đau hạ sườn phải"}
    assert not turn2_v27.keep_semantic_expansion(
        expansion("đau hạ sườn", end=len("đau hạ sườn")),
        texts,
    )


def test_semantic_filter_keeps_complete_clinical_span() -> None:
    texts = {"1": "đau bụng vùng hạ sườn phải"}
    assert turn2_v27.keep_semantic_expansion(
        expansion("đau bụng vùng hạ sườn phải"),
        texts,
    )
