from pathlib import Path

from scripts.train_vimedner import entity_set, read_conll, strict_metrics


def test_entity_set_decodes_bio_and_repairs_orphan_inside() -> None:
    assert entity_set(
        ["O", "B-ten_benh", "I-ten_benh", "O", "I-trieu_chung_benh"]
    ) == {
        (1, 3, "ten_benh"),
        (4, 5, "trieu_chung_benh"),
    }


def test_strict_metrics_requires_exact_boundaries() -> None:
    metrics = strict_metrics(
        [["B-ten_benh", "I-ten_benh", "O", "B-trieu_chung_benh"]],
        [["B-ten_benh", "O", "O", "B-trieu_chung_benh"]],
    )
    assert metrics["micro"]["tp"] == 1
    assert metrics["micro"]["fp"] == 1
    assert metrics["micro"]["fn"] == 1
    assert metrics["micro"]["f1"] == 0.5
    assert metrics["target"]["f1"] == 0.5


def test_target_metric_ignores_labels_unused_by_pipeline() -> None:
    metrics = strict_metrics(
        [["B-ten_benh", "O", "B-bien_phap_dieu_tri"]],
        [["B-ten_benh", "O", "O"]],
    )
    assert metrics["micro"]["f1"] < 1.0
    assert metrics["target"]["f1"] == 1.0


def test_read_conll_skips_the_known_empty_token_row(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text(
        "ung B-ten_benh\n"
        "thư I-ten_benh\n"
        " B-bien_phap_dieu_tri\n"
        "\n"
        "đau B-trieu_chung_benh\n",
        encoding="utf-8",
    )
    sentences = read_conll(source)
    assert [sentence.tokens for sentence in sentences] == [
        ["ung", "thư"],
        ["đau"],
    ]
