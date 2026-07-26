from src.clinical_mentions.turn2_v18 import (
    is_polar_question_mention,
    prune_polar_question_diagnoses,
    trim_symptom_reporting_prefixes,
)


def entity(text: str, surface: str, entity_type: str) -> dict:
    start = text.index(surface)
    return {
        "text": surface,
        "type": entity_type,
        "position": [start, start + len(surface)],
        "assertions": [],
        "candidates": [],
    }


def test_prunes_diagnosis_that_is_only_polar_question_focus() -> None:
    text = "Tình trạng của em có phải là tăng HA thật sự không ạ?"
    diagnosis = entity(text, "tăng HA", "CHẨN_ĐOÁN")
    assert is_polar_question_mention(text, diagnosis)
    assert prune_polar_question_diagnoses(text, [diagnosis]) == []


def test_keeps_non_diagnosis_in_same_question() -> None:
    text = "Có phải là đau bụng thật sự không?"
    symptom = entity(text, "đau bụng", "TRIỆU_CHỨNG")
    assert prune_polar_question_diagnoses(text, [symptom]) == [symptom]


def test_trims_reporting_prefix_and_updates_offset() -> None:
    text = "Miệng thấy hơi thở mùi khó chịu."
    symptom = entity(
        text,
        "Miệng thấy hơi thở mùi khó chịu",
        "TRIỆU_CHỨNG",
    )
    refined = trim_symptom_reporting_prefixes(text, [symptom])
    assert refined[0]["text"] == "hơi thở mùi khó chịu"
    assert text[slice(*refined[0]["position"])] == refined[0]["text"]
