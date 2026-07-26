from src.clinical_mentions import turn2_v25


def symptom(text: str, start: int = 10) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": [],
        "position": [start, start + len(text)],
    }


def test_trims_reporting_prefix_and_preserves_end_offset() -> None:
    source = symptom("miệng thấy hơi thở mùi khó chịu")
    refined, changed = turn2_v25.trim_reporting_prefix(source)
    assert changed
    assert refined["text"] == "hơi thở mùi khó chịu"
    assert refined["position"] == [21, source["position"][1]]
    assert refined["assertions"] == source["assertions"]


def test_supports_optional_cognitive_verb() -> None:
    source = symptom("mồm cảm thấy có mùi khó chịu")
    refined, changed = turn2_v25.trim_reporting_prefix(source)
    assert changed
    assert refined["text"] == "có mùi khó chịu"


def test_does_not_change_an_unrelated_symptom() -> None:
    source = symptom("mất thị lực")
    refined, changed = turn2_v25.trim_reporting_prefix(source)
    assert not changed
    assert refined == source


def test_does_not_change_a_non_symptom() -> None:
    source = {
        **symptom("miệng thấy tổn thương"),
        "type": "CHẨN_ĐOÁN",
        "candidates": ["K13.70"],
    }
    refined, changed = turn2_v25.trim_reporting_prefix(source)
    assert not changed
    assert refined == source
