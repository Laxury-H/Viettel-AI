from src.clinical_mentions import turn2_v32


def entity(
    surface: str,
    start: int,
    assertions: list[str] | None = None,
) -> dict:
    return {
        "text": surface,
        "type": "TRIỆU_CHỨNG",
        "assertions": assertions or [],
        "position": [start, start + len(surface)],
    }


def test_direct_relative_subject_gets_family_assertion() -> None:
    text = "Như vậy Mẹ của bạn đã bắt đầu bị run tay."
    start = text.index("run tay")
    output, changes = turn2_v32.repair_direct_family_assertions(
        {"1": text},
        {"1": [entity("run tay", start)]},
    )
    assert output["1"][0]["assertions"] == ["isFamily"]
    assert len(changes) == 1


def test_generic_symptom_statement_is_not_family() -> None:
    text = "Thuốc có thể gây run tay ở một số người."
    start = text.index("run tay")
    output, changes = turn2_v32.repair_direct_family_assertions(
        {"1": text},
        {"1": [entity("run tay", start)]},
    )
    assert output["1"][0]["assertions"] == []
    assert changes == []


def test_family_assertion_keeps_official_order() -> None:
    text = "Bé bị bệnh bàn chân bẹt."
    start = text.index("bệnh bàn chân bẹt")
    output, _ = turn2_v32.repair_direct_family_assertions(
        {"1": text},
        {
            "1": [
                entity(
                    "bệnh bàn chân bẹt",
                    start,
                    ["isNegated", "isHistorical"],
                )
            ]
        },
    )
    assert output["1"][0]["assertions"] == [
        "isNegated",
        "isFamily",
        "isHistorical",
    ]


def test_unreviewed_surface_is_not_changed() -> None:
    text = "Bé bị sốt."
    start = text.index("sốt")
    output, changes = turn2_v32.repair_direct_family_assertions(
        {"1": text},
        {"1": [entity("sốt", start)]},
    )
    assert output["1"][0]["assertions"] == []
    assert changes == []
