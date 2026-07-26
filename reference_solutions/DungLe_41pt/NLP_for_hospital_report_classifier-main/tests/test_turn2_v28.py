from src.clinical_mentions import turn2_v28


def symptom(text: str, start: int) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": [],
        "position": [start, start + len(text)],
    }


def test_repeated_lines_recover_a_globally_accepted_surface() -> None:
    line = (
        "Khám lâm sàng ghi nhận mất định hướng và đi lại không vững "
        "theo lời kể người nhà."
    )
    texts = {
        "1": line,
        "2": line,
        "3": "mất định hướng; mất định hướng",
    }
    first_start = line.index("mất định hướng")
    control = {
        "1": [symptom("mất định hướng", first_start)],
        "2": [],
        "3": [
            symptom("mất định hướng", 0),
            symptom("mất định hướng", len("mất định hướng; ")),
        ],
    }
    additions = turn2_v28.derive_repeated_surface_additions(texts, control)
    assert [
        (
            addition.record_id,
            addition.surface,
            addition.start,
        )
        for addition in additions
    ] == [("2", "mất định hướng", first_start)]


def test_does_not_learn_a_singleton_surface() -> None:
    line = "Bệnh nhân có một biểu hiện thần kinh kéo dài trong nhiều ngày."
    start = line.index("biểu hiện")
    texts = {"1": line, "2": line}
    control = {
        "1": [symptom("biểu hiện", start)],
        "2": [],
    }
    assert turn2_v28.derive_repeated_surface_additions(texts, control) == []
