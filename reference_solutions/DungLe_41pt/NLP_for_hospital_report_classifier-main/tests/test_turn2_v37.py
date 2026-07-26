from copy import deepcopy

from src.clinical_mentions import turn2_v37


def entity(text: str, assertions: list[str], start: int) -> dict:
    return {
        "text": text,
        "type": "CHẨN_ĐOÁN",
        "candidates": ["I10"],
        "assertions": assertions,
        "position": [start, start + len(text)],
    }


def test_inline_history_adds_historical() -> None:
    text = "Bệnh nhân khó thở, tiền sử: suy tim - tăng huyết áp\n"
    start = text.index("suy tim")
    source = {"1": [entity("suy tim", [], start)]}
    output, changes = turn2_v37.repair_vietnamese_assertions(
        {"1": text}, deepcopy(source)
    )
    assert output["1"][0]["assertions"] == ["isHistorical"]
    assert len(changes) == 1


def test_denied_personal_history_adds_two_assertions() -> None:
    text = "Tiền sử bản thân: chưa bị vàng da, vàng mắt trước đó.\n"
    start = text.index("vàng da")
    source = {
        "1": [
            {
                **entity("vàng da", [], start),
                "type": "TRIỆU_CHỨNG",
                "candidates": [],
            }
        ]
    }
    output, changes = turn2_v37.repair_vietnamese_assertions(
        {"1": text}, deepcopy(source)
    )
    assert output["1"][0]["assertions"] == ["isNegated", "isHistorical"]
    assert len(changes) == 1


def test_generic_risk_factor_is_not_family_assertion() -> None:
    text = (
        "Yếu tố nguy cơ\nKhông thay đổi được\n"
        "Tiền sử gia đình bệnh tim mạch sớm\n"
    )
    start = text.index("bệnh tim mạch")
    source = {"1": [entity("bệnh tim mạch", ["isFamily"], start)]}
    output, changes = turn2_v37.repair_vietnamese_assertions(
        {"1": text}, deepcopy(source)
    )
    assert output["1"][0]["assertions"] == []
    assert len(changes) == 1
