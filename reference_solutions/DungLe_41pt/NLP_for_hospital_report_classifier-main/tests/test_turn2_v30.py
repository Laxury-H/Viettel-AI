from src.clinical_mentions import turn2_v30


def symptom(text: str, start: int) -> dict:
    return {
        "text": text,
        "type": "TRIỆU_CHỨNG",
        "assertions": [],
        "position": [start, start + len(text)],
    }


def diagnosis(text: str, candidates: list[str]) -> dict:
    return {
        "text": text,
        "type": "CHẨN_ĐOÁN",
        "candidates": candidates,
        "assertions": [],
        "position": [0, len(text)],
    }


def test_accepted_boundary_does_not_turn_knee_pain_into_headache() -> None:
    accepted = "Bệnh nhân đau đầu kéo dài."
    knee = "Dùng NSAID để điều trị đau đầu gối."
    texts = {"1": accepted, "2": knee}
    control = {
        "1": [symptom("đau đầu", accepted.index("đau đầu"))],
        "2": [symptom("đau", knee.index("đau"))],
    }
    expansions = turn2_v30.derive_accepted_boundary_expansions(
        texts,
        control,
    )
    assert [
        (
            expansion.record_id,
            expansion.after_text,
        )
        for expansion in expansions
    ] == []


def test_safe_diagnosis_rejects_polar_question_focus() -> None:
    question = "Tình trạng này có phải là tăng HA thật sự không?"
    history = "Phát hiện tăng HA từ năm 2009."
    texts = {"1": question, "2": history}
    control = {"1": [], "2": []}
    additions = turn2_v30.derive_safe_diagnosis_additions(texts, control)
    assert [
        (addition.record_id, addition.surface, addition.candidate)
        for addition in additions
    ] == [("2", "tăng HA", "I10")]


def test_contextual_candidate_pruning() -> None:
    gerd = "trào ngược dạ dày thực quản"
    anemia = "thiếu máu tan huyết do thiếu men G6PD"
    records = {
        "1": [diagnosis(gerd, ["K21.0", "K21.9"])],
        "2": [
            {
                **diagnosis("thiếu máu tan huyết", ["D59.9", "D55.0"]),
                "position": [0, len("thiếu máu tan huyết")],
            }
        ],
    }
    output, changes = turn2_v30.keep_one_contextual_candidate(
        {"1": gerd, "2": anemia},
        records,
    )
    assert output["1"][0]["candidates"] == ["K21.9"]
    assert output["2"][0]["candidates"] == ["D55.0"]
    assert len(changes) == 2


def test_diagnosis_first_detected_in_prior_year_is_historical() -> None:
    text = "Tiền sử bản thân:\nPhát hiện tăng HA từ năm 2009."
    addition = turn2_v30.DiagnosisAddition(
        record_id="1",
        start=text.index("tăng HA"),
        end=text.index("tăng HA") + len("tăng HA"),
        surface="tăng HA",
        candidate="I10",
    )
    output, _ = turn2_v30.apply_diagnosis_additions(
        {"1": text},
        {"1": []},
        [addition],
    )
    assert output["1"][0]["assertions"] == ["isHistorical"]
