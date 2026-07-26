# Bài 2: Ontological Reasoning in Medical Knowledge Retrieval

**Mục tiêu cốt lõi:** Xây dựng hệ thống AI xử lý văn bản y khoa tự do (ghi chú lâm sàng, giấy xuất viện, kết quả xét nghiệm, hồ sơ EHR).

**Các yêu cầu thực hiện chính:**
- **Nhận diện và phân loại:** Phát hiện các khái niệm y tế xuất hiện trong văn bản, bao gồm: triệu chứng, kết quả xét nghiệm, bệnh lý, thuốc và thông tin bệnh nhân.
- **Chuẩn hóa (Mapping):** Ánh xạ bệnh lý theo chuẩn phân loại ICD-10 và ánh xạ thuốc theo chuẩn RxNorm.
- **Suy luận ngữ cảnh:** Xác định các thuộc tính ngữ cảnh của thông tin như tính phủ định, liên quan đến người nhà, hoặc thuộc về tiền sử.
- **Xác định quan hệ:** Rút trích và suy luận mối liên hệ giữa các khái niệm y tế đã nhận diện trong văn bản.

## 1. Hình thức nộp bài
* Kết quả dự đoán nộp dưới định dạng file JSON.
* File nộp là một tệp `output.zip`, giải nén ra cấu trúc sau:
  ```text
  output/
      ├── 1.json     # Nhãn của bản ghi 1
      ├── 2.json     # Nhãn của bản ghi 2
      ├── …
      └── 100.json
  ```
* **Lưu ý phần cứng/mô hình:** Thí sinh tự chuẩn bị tài nguyên. Với giải pháp LLM/agent, chỉ được phép self-host model tối đa **9B params** (không dùng API ngoài).

## 2. Dữ liệu Input / Output mẫu

**Input:**
```text
Danh sách thuốc trước nhập viện chính xác và đầy đủ. 1. amlodipine 10 mg po daily 2. aspirin 81 mg po daily 3. metoprolol succinate xl 50 mg po daily 4. guaifenesin ml po q6h:prn điều trị ho 5. nystatin oral suspension 5 ml po qid:prn điều trị đau nhức 6. acetaminophen 325-650 mg po q6h:prn điều trị sốt đau 7. pravastatin 40 mg po daily 8. docusate sodium 100 mg po bid điều trị táo bón 9. senna 8.6 mg po bid:prn điều trị táo bón 10. clonazepam 0.5 mg po qam:prn điều trị lo âu 11. clonazepam 1.5 mg po qhs điều trị lo âu mất ngủ
```

**Output:**
```json
[
  {
    "text": "amlodipine 10 mg po daily",
    "type": "THUỐC",
    "candidates": ["308135"],
    "assertions": ["isHistorical"],
    "position": [58, 83]
  },
  {
    "text": "aspirin 81 mg po daily",
    "type": "THUỐC",
    "candidates": ["243670"],
    "assertions": ["isHistorical"],
    "position": [89, 111]
  },
  {
    "text": "metoprolol succinate xl 50 mg po daily",
    "type": "THUỐC",
    "candidates": ["866436"],
    "assertions": ["isHistorical"],
    "position": [117, 155]
  },
  {
    "text": "guaifenesin ml po q6h:prn",
    "type": "THUỐC",
    "candidates": ["392085"],
    "assertions": ["isHistorical"],
    "position": [161, 186]
  },
  {
    "text": "ho",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [196, 198]
  },
  {
    "text": "nystatin oral suspension 5 ml po qid:prn",
    "type": "THUỐC",
    "candidates": ["7597"],
    "assertions": ["isHistorical"],
    "position": [204, 244]
  },
  {
    "text": "đau nhức",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [254, 262]
  },
  {
    "text": "acetaminophen 325-650 mg po q6h:prn",
    "type": "THUỐC",
    "candidates": ["313782"],
    "assertions": ["isHistorical"],
    "position": [268, 303]
  },
  {
    "text": "sốt đau",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [313, 320]
  },
  {
    "text": "pravastatin 40 mg po daily",
    "type": "THUỐC",
    "candidates": ["904475"],
    "assertions": ["isHistorical"],
    "position": [326, 352]
  },
  {
    "text": "docusate sodium 100 mg po bid",
    "type": "THUỐC",
    "candidates": ["1099279"],
    "assertions": ["isHistorical"],
    "position": [358, 387]
  },
  {
    "text": "táo bón",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [397, 404]
  },
  {
    "text": "senna 8.6 mg po bid:prn",
    "type": "THUỐC",
    "candidates": ["312935"],
    "assertions": ["isHistorical"],
    "position": [410, 433]
  },
  {
    "text": "táo bón",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [443, 450]
  },
  {
    "text": "clonazepam 0.5 mg po qam:prn",
    "type": "THUỐC",
    "candidates": ["197527"],
    "assertions": ["isHistorical"],
    "position": [457, 485]
  },
  {
    "text": "lo âu",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [495, 500]
  },
  {
    "text": "clonazepam 1.5 mg po qhs",
    "type": "THUỐC",
    "candidates": ["197528"],
    "assertions": ["isHistorical"],
    "position": [507, 531]
  },
  {
    "text": "lo âu",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [541, 546]
  },
  {
    "text": "mất ngủ",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [547, 554]
  }
]
```

## 3. Metric đánh giá

* **Công thức tính điểm tổng:** `final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score`
* **text_score (Xác định tên khái niệm):** Đánh giá bằng Word Error Rate (WER).
* **assertions_score (Xác định assertions):** Độ tương đồng Jaccard (Jaccard similarity), lấy trung bình.
* **candidates_score (Xác định candidates):** Độ tương đồng Jaccard (Jaccard similarity).
* **Quy tắc phạt:** Nếu dự đoán đúng `text` nhưng sai `type` (VD: đoán `CHẨN_ĐOÁN` nhưng đáp án là `TRIỆU_CHỨNG`), hệ thống sẽ tính là 1 khái niệm mới sai hoàn toàn và chấm 0 điểm ở cả 3 metric.
