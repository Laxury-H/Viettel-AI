"""Deterministic regression checks for the v4.1 inference rules."""

from __future__ import annotations

import unittest

from run import OFFICIAL_TYPES, extract


class ExtractionRegressionTests(unittest.TestCase):
    def _entities(self, text: str, *, profile: str = "balanced") -> list[dict]:
        entities = extract(text, profile=profile)
        for entity in entities:
            start, end = entity["position"]
            self.assertEqual(text[start:end], entity["text"])
            self.assertIn(entity["type"], OFFICIAL_TYPES)
            self.assertEqual(len(entity["position"]), 2)
            if entity["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                self.assertTrue(entity.get("candidates"))
            else:
                self.assertNotIn("candidates", entity)
        return entities

    @staticmethod
    def _find(entities: list[dict], text: str, entity_type: str) -> list[dict]:
        return [
            entity
            for entity in entities
            if entity["text"].casefold() == text.casefold()
            and entity["type"] == entity_type
        ]

    def test_allergy_and_resistance_are_not_treatment_drugs(self) -> None:
        text = (
            "Dị ứng: Dị ứng furosemide. "
            "Nhiễm trùng do Enterococcus kháng vancomycin. "
            "Điều trị: vancomycin 1 gram."
        )
        entities = self._entities(text)
        drugs = [entity for entity in entities if entity["type"] == "THUỐC"]
        self.assertEqual([entity["text"] for entity in drugs], ["vancomycin 1 gram"])
        self.assertEqual(drugs[0]["candidates"], ["1807513"])

    def test_migraine_is_symptom_unless_diagnostic_context_is_explicit(self) -> None:
        text = "Bệnh nhân đau nửa đầu. Bác sĩ chẩn đoán bệnh đau nửa đầu Migraine."
        entities = self._entities(text)
        self.assertTrue(self._find(entities, "đau nửa đầu", "TRIỆU_CHỨNG"))
        diagnoses = [entity for entity in entities if entity["type"] == "CHẨN_ĐOÁN"]
        self.assertTrue(any("Migraine" in entity["text"] for entity in diagnoses))
        self.assertTrue(all(entity["candidates"] == ["G43.909"] for entity in diagnoses))

    def test_treatment_class_phrases_do_not_create_inner_symptoms(self) -> None:
        text = "Dùng thuốc hạ sốt, thuốc chống nôn và thuốc chống trầm cảm."
        entities = self._entities(text)
        forbidden = {"sốt", "nôn", "trầm cảm"}
        self.assertFalse(any(entity["text"].casefold() in forbidden for entity in entities))

    def test_treatment_wording_can_still_assert_a_patient_diagnosis(self) -> None:
        text = "Bệnh nhân đã dùng thuốc điều trị ĐTD typ II, hiện đã ngừng thuốc."
        diagnoses = [
            entity
            for entity in self._entities(text)
            if entity["type"] == "CHẨN_ĐOÁN"
        ]
        self.assertEqual([entity["text"] for entity in diagnoses], ["ĐTD typ II"])
        self.assertEqual(diagnoses[0]["candidates"], ["E11.9"])

    def test_future_test_scope_ends_at_later_clinical_heading(self) -> None:
        text = (
            "Xét nghiệm cần làm:\nCông thức máu\n"
            "Chẩn đoán: tăng huyết áp\nĐiều trị:\n"
            "So với chụp CT đầu từ lần nhập viện trước."
        )
        entities = self._entities(text)
        test_names = [
            entity["text"]
            for entity in entities
            if entity["type"] == "TÊN_XÉT_NGHIỆM"
        ]
        self.assertNotIn("Công thức máu", test_names)
        self.assertIn("CT", test_names)

    def test_vital_signs_are_linked_and_false_intravenous_pulse_is_rejected(self) -> None:
        text = (
            "M: 82 ck/ph; HA: 160/80 mmHg; Nhịp tim đều, 85 lần/phút; "
            "SpO2 từ 88-92 %; Truyền dịch tĩnh mạch 750cc."
        )
        entities = self._entities(text)
        names = {
            entity["text"]
            for entity in entities
            if entity["type"] == "TÊN_XÉT_NGHIỆM"
        }
        results = {
            entity["text"]
            for entity in entities
            if entity["type"] == "KẾT_QUẢ_XÉT_NGHIỆM"
        }
        self.assertTrue({"M", "HA", "Nhịp tim", "SpO2"}.issubset(names))
        self.assertTrue({"82 ck/ph", "160/80 mmHg", "85 lần/phút", "88-92 %"}.issubset(results))
        self.assertNotIn("750", results)

    def test_strength_and_brand_specific_rxnorm_overrides(self) -> None:
        cases = {
            "Crestor": "320864",
            "Suboxone": "352990",
            "Klonopin": "202585",
            "Coumadin 3 mg": "855320",
            "Medrol 16 mg": "207138",
            "Zestril 10 mg": "104377",
            "80 mg po Lasix": "205732",
            "metoprolol 25 mg po bid": "866924",
        }
        for mention, expected in cases.items():
            with self.subTest(mention=mention):
                entities = self._entities(f"Điều trị: {mention}.")
                drugs = [entity for entity in entities if entity["type"] == "THUỐC"]
                self.assertEqual(len(drugs), 1)
                self.assertEqual(drugs[0]["candidates"], [expected])

    def test_context_specific_icd_overrides(self) -> None:
        cases = (
            ("Bên phải âm tính với huyết khối tĩnh mạch sâu.", "I82.401"),
            ("Chụp x-quang bàn chân phải không phát hiện gãy xương.", "S92.901A"),
            ("Tiền sử giai đoạn trầm cảm.", "F32.9"),
            ("Chẩn đoán trầm cảm.", "F32.A"),
            ("Chẩn đoán cơn tim nhanh nhĩ.", "I47.19"),
            ("Chẩn đoán nhịp nhanh trên thất.", "I47.10"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                diagnoses = [
                    entity
                    for entity in self._entities(text)
                    if entity["type"] == "CHẨN_ĐOÁN"
                ]
                self.assertTrue(diagnoses)
                self.assertIn(expected, diagnoses[0]["candidates"])

    def test_family_scope_and_present_symptom_override_history_heading(self) -> None:
        text = (
            "1. Tiền sử bệnh\n"
            "Nhưng hiện tượng run tay không khỏi hẳn; em muốn hỏi mẹ em nên làm gì."
        )
        symptoms = [
            entity
            for entity in self._entities(text)
            if entity["text"].casefold() == "run tay"
        ]
        self.assertTrue(symptoms)
        self.assertIn("isFamily", symptoms[0]["assertions"])
        self.assertNotIn("isHistorical", symptoms[0]["assertions"])

    def test_family_scope_carries_across_a_single_relative_subject_line(self) -> None:
        text = "Em trai mình đi khám, bác sĩ chẩn đoán giãn thừng tinh và thỉnh thoảng đau."
        entities = self._entities(text)
        family_entities = [
            entity
            for entity in entities
            if entity["text"].casefold() in {"giãn thừng tinh", "đau"}
        ]
        self.assertEqual(len(family_entities), 2)
        self.assertTrue(
            all("isFamily" in entity["assertions"] for entity in family_entities)
        )

    def test_historical_cues_cover_coordinated_clause_and_stopped_medication(self) -> None:
        text = (
            "Triệu chứng cách đây vài năm: buồn nôn và tiêu chảy.\n"
            "Gần đây ngừng sử dụng omeprazole để làm xét nghiệm."
        )
        entities = self._entities(text)
        target = [
            entity
            for entity in entities
            if entity["text"].casefold() in {"buồn nôn", "tiêu chảy", "omeprazole"}
        ]
        self.assertEqual(len(target), 3)
        self.assertTrue(all("isHistorical" in entity["assertions"] for entity in target))

    def test_current_onset_does_not_inherit_later_discharge_cue(self) -> None:
        text = (
            "Thời điểm khởi phát triệu chứng: vài ngày mệt mỏi\n"
            "Diễn biến: điều trị ổn định, sau đó xuất viện."
        )
        symptom = self._find(self._entities(text), "mệt mỏi", "TRIỆU_CHỨNG")[0]
        self.assertNotIn("isHistorical", symptom["assertions"])

    def test_current_illness_started_earlier_is_not_automatically_history(self) -> None:
        text = "Bệnh nhân tiểu ít, bệnh khởi phát cách đây 1 tháng và đang tiếp diễn."
        symptom = self._find(self._entities(text), "tiểu ít", "TRIỆU_CHỨNG")[0]
        self.assertNotIn("isHistorical", symptom["assertions"])

    def test_current_drug_is_not_history_because_another_drug_was_stopped(self) -> None:
        text = "Đã dừng vanco; hiện tại đang dùng bactrim để điều trị."
        drugs = [entity for entity in self._entities(text) if entity["type"] == "THUỐC"]
        assertions = {entity["text"].casefold(): entity["assertions"] for entity in drugs}
        self.assertIn("isHistorical", assertions["vanco"])
        self.assertNotIn("isHistorical", assertions["bactrim"])

    def test_negated_prior_condition_has_both_assertions(self) -> None:
        text = "Bệnh nhân không xác nhận đã bị trầm cảm trước đó."
        diagnosis = self._find(self._entities(text), "trầm cảm", "CHẨN_ĐOÁN")[0]
        self.assertIn("isNegated", diagnosis["assertions"])
        self.assertIn("isHistorical", diagnosis["assertions"])

    def test_low_probability_imaging_statement_is_negated(self) -> None:
        text = "Xạ hình cho thấy xác suất thấp thuyên tắc phổi."
        diagnosis = self._find(
            self._entities(text), "thuyên tắc phổi", "CHẨN_ĐOÁN"
        )[0]
        self.assertIn("isNegated", diagnosis["assertions"])


if __name__ == "__main__":
    unittest.main()
