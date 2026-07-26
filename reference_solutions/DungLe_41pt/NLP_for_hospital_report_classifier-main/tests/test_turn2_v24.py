from src.clinical_mentions import turn2_v24


def symptom(text: str, start: int) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": [],
        "position": [start, start + len(text)],
    }


def test_prunes_rejected_surface_when_it_is_candidate_only() -> None:
    control = [symptom("đau đầu", 0)]
    candidate = [*control, symptom("Đỏ mắt", 20)]
    refined, removed = turn2_v24.prune_rejected_additions(control, candidate)
    assert refined == control
    assert removed == [symptom("Đỏ mắt", 20)]


def test_preserves_rejected_surface_when_already_in_control() -> None:
    control = [symptom("đỏ mắt", 20)]
    refined, removed = turn2_v24.prune_rejected_additions(control, control)
    assert refined == control
    assert removed == []


def test_does_not_prune_other_high_confidence_additions() -> None:
    control: list[dict] = []
    candidate = [
        symptom("weak", 10),
        symptom("tê bì", 20),
        symptom("mù vĩnh viễn", 30),
    ]
    refined, removed = turn2_v24.prune_rejected_additions(control, candidate)
    assert refined == candidate
    assert removed == []
