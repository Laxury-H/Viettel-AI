from __future__ import annotations

import unittest

from clinical_mentions import pipeline
from clinical_mentions import rules


class RepeatedLineConsensusTests(unittest.TestCase):
    line = (
        "Không ghi nhận co giật, cứng đờ, cắn lưỡi hoặc "
        "tiểu tiện không tự chủ."
    )
    symptom = "tiểu tiện không tự chủ"
    symptom_type = "TRIỆU_CHỨNG"

    def make_fixture(
        self,
        support_start: int,
        support_end: int,
    ) -> tuple[dict[str, str], dict[str, list[dict]], dict[str, list[dict]]]:
        start = self.line.index(self.symptom)
        end = start + len(self.symptom)
        historical, family = rules.section_states(self.line)
        source_entity = rules.make_entity(
            self.line,
            rules.Span(start, end),
            self.symptom_type,
            historical,
            family,
        )
        texts = {"1": self.line, "2": self.line}
        teacher = {
            "1": [],
            "2": [
                {
                    "start": support_start,
                    "end": support_end,
                    "type": self.symptom_type,
                    "confidence": 0.97,
                }
            ],
        }
        outputs = {"1": [source_entity], "2": []}
        return texts, teacher, outputs

    def test_repairs_anchored_teacher_fragment(self) -> None:
        start = self.line.index(self.symptom)
        fragment_end = start + len("tiểu tiện")
        texts, teacher, outputs = self.make_fixture(start, fragment_end)

        added = pipeline._apply_repeated_line_consensus(
            texts,
            teacher,
            outputs,
        )

        self.assertEqual(added, 1)
        self.assertEqual(outputs["2"][0]["text"], self.symptom)
        self.assertEqual(outputs["2"][0]["assertions"], ["isNegated"])

    def test_rejects_unanchored_teacher_fragment(self) -> None:
        start = self.line.index(self.symptom) + len("tiểu ")
        end = start + len("tiện")
        texts, teacher, outputs = self.make_fixture(start, end)

        added = pipeline._apply_repeated_line_consensus(
            texts,
            teacher,
            outputs,
        )

        self.assertEqual(added, 0)
        self.assertEqual(outputs["2"], [])


class QuestionDiagnosisPruningTests(unittest.TestCase):
    def test_production_prunes_diagnosis_in_polar_question(self) -> None:
        text = "Tình trạng này có phải là tăng HA thật sự không?"
        start = text.index("tăng HA")
        entity = {
            "text": "tăng HA",
            "type": "CHẨN_ĐOÁN",
            "candidates": ["I10"],
            "assertions": ["isNegated"],
            "position": [start, start + len("tăng HA")],
        }

        refined = pipeline._refine_entities(
            text,
            [entity],
            prune_polar_questions=True,
        )

        self.assertEqual(refined, [])

    def test_production_keeps_diagnosis_outside_polar_question(self) -> None:
        text = "Chẩn đoán xác định tăng HA."
        start = text.index("tăng HA")
        entity = {
            "text": "tăng HA",
            "type": "CHẨN_ĐOÁN",
            "candidates": ["I10"],
            "assertions": [],
            "position": [start, start + len("tăng HA")],
        }

        refined = pipeline._refine_entities(
            text,
            [entity],
            prune_polar_questions=True,
        )

        self.assertEqual(refined, [entity])


class SymptomBoundaryTests(unittest.TestCase):
    def test_v23_trims_reporting_prefix_from_symptom(self) -> None:
        text = "Bệnh nhân miệng thấy hơi thở mùi khó chịu."
        surface = "miệng thấy hơi thở mùi khó chịu"
        start = text.index(surface)
        entity = {
            "text": surface,
            "type": "TRIỆU_CHỨNG",
            "assertions": [],
            "position": [start, start + len(surface)],
        }

        refined = pipeline._refine_entities(
            text,
            [entity],
            prune_polar_questions=True,
            trim_symptom_reporting_prefix=True,
        )

        self.assertEqual(refined[0]["text"], "hơi thở mùi khó chịu")
        self.assertEqual(
            refined[0]["position"],
            [text.index("hơi thở"), start + len(surface)],
        )


if __name__ == "__main__":
    unittest.main()
