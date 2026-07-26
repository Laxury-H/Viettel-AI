from src.clinical_mentions import turn2_v29


def symptom(text: str, start: int, *, negated: bool = False) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": ["isNegated"] if negated else [],
        "position": [start, start + len(text)],
    }


def test_recovers_only_missing_occurrences_of_selected_surfaces() -> None:
    first = "Bệnh nhân mất định hướng rồi tỉnh chậm."
    second = "Không ghi nhận cứng đờ."
    texts = {"1": first, "2": second}
    control = {
        "1": [symptom("mất định hướng", first.index("mất định hướng"))],
        "2": [],
    }
    additions, evidence = turn2_v29.derive_selected_recall_additions(
        texts,
        control,
        surfaces=("mất định hướng", "cứng đờ"),
    )
    assert [
        (item.record_id, item.surface, item.start, item.end)
        for item in additions
    ] == [
        (
            "2",
            "cứng đờ",
            second.index("cứng đờ"),
            second.index("cứng đờ") + len("cứng đờ"),
        )
    ]
    assert evidence[0]["accepted_occurrences_in_control"] == 0


def test_rejects_surface_outside_teacher_lexicon() -> None:
    try:
        turn2_v29.derive_selected_recall_additions(
            {"1": "một chuỗi không hợp lệ"},
            {"1": []},
            surfaces=("một chuỗi không hợp lệ",),
        )
    except ValueError as error:
        assert "teacher lexicon" in str(error)
    else:
        raise AssertionError("Expected a lexicon validation error")
