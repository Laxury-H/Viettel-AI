from src.clinical_mentions import turn2_v33


def entity(
    surface: str,
    start: int,
    assertions: list[str] | None = None,
) -> dict:
    return {
        "text": surface,
        "type": "CHẨN_ĐOÁN",
        "assertions": assertions or [],
        "position": [start, start + len(surface)],
    }


def test_relative_primary_patient_loses_family_assertion() -> None:
    text = "Câu hỏi của người dùng: Mẹ em bị bệnh mạch vành đã nhiều năm."
    start = text.index("bệnh mạch vành")
    output, changes = turn2_v33.repair_primary_patient_family_scope(
        {"1": text},
        {"1": [entity("bệnh mạch vành", start, ["isFamily", "isHistorical"])]},
    )
    assert output["1"][0]["assertions"] == ["isHistorical"]
    assert len(changes) == 1


def test_true_family_history_is_preserved() -> None:
    text = "Tiền sử gia đình: không ai bị viêm gan B."
    start = text.index("viêm gan B")
    output, changes = turn2_v33.repair_primary_patient_family_scope(
        {"1": text},
        {"1": [entity("viêm gan B", start, ["isNegated", "isFamily"])]},
    )
    assert output["1"][0]["assertions"] == ["isNegated", "isFamily"]
    assert changes == []


def test_secondary_family_event_is_preserved() -> None:
    text = "Sự kiện trước nhập viện: Vợ được chẩn đoán giãn phế quản."
    start = text.index("giãn phế quản")
    output, changes = turn2_v33.repair_primary_patient_family_scope(
        {"1": text},
        {"1": [entity("giãn phế quản", start, ["isFamily", "isHistorical"])]},
    )
    assert output["1"][0]["assertions"] == ["isFamily", "isHistorical"]
    assert changes == []


def test_hypothetical_child_risk_is_preserved() -> None:
    text = "Nếu gen truyền sang con bạn thì con bạn có thể bị tắc mạch."
    start = text.index("tắc mạch")
    output, changes = turn2_v33.repair_primary_patient_family_scope(
        {"1": text},
        {"1": [entity("tắc mạch", start, ["isFamily"])]},
    )
    assert output["1"][0]["assertions"] == ["isFamily"]
    assert changes == []


def test_non_family_assertions_are_unchanged_in_relative_consultation() -> None:
    text = "Câu hỏi từ người dùng: Ông em từng bị bệnh gút, hiện đang đau."
    start = text.index("đau")
    output, changes = turn2_v33.repair_primary_patient_family_scope(
        {"1": text},
        {"1": [entity("đau", start, ["isHistorical"])]},
    )
    assert output["1"][0]["assertions"] == ["isHistorical"]
    assert changes == []
