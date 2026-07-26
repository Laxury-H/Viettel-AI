from scripts.calibrate_teacher_consensus import (
    consensus_predictions,
    decode_words,
)


def test_decode_words_repairs_orphan_inside_and_averages_confidence() -> None:
    assert decode_words(
        {
            0: ("I-ten_benh", 0.8),
            1: ("I-ten_benh", 1.0),
            2: ("O", 0.9),
            3: ("B-trieu_chung_benh", 0.7),
        },
        4,
    ) == {
        (0, 2, "ten_benh"): 0.9,
        (3, 4, "trieu_chung_benh"): 0.7,
    }


def test_consensus_requires_exact_span_type_and_both_thresholds() -> None:
    first = [
        {
            (0, 1, "ten_benh"): 0.99,
            (2, 4, "trieu_chung_benh"): 0.98,
        }
    ]
    second = [
        {
            (0, 1, "ten_benh"): 0.95,
            (2, 3, "trieu_chung_benh"): 0.99,
        }
    ]
    assert consensus_predictions(first, second, 0.98, 0.90) == [
        {(0, 1, "ten_benh")}
    ]
