# Viettel AI - Clinical Mention Extraction Project

Dự án tham gia cuộc thi **Viettel AI Race 2026** - Trích xuất thực thể lâm sàng từ hồ sơ bệnh án tiếng Việt (Vietnamese Clinical Mention Extraction).

---

## 📁 Cấu trúc Kho Lưu trữ (Repository Layout)

```text
d:\Project\Viettel AI\
├── docs/                        # Tài liệu cuộc thi & Đề bài
│   ├── AI Race 2026 - Cuộc đua AI cho kỹ sư Việt Nam.pdf
│   └── Problem_Statement.md    # Mô tả đề bài chi tiết
│
├── data/                        # Dữ liệu vào / ra chính
│   └── raw/                     # Tập dữ liệu 100 hồ sơ bệnh án (1.txt - 100.txt)
│
├── submissions/                 # Đóng gói và lưu trữ nộp bài
│   ├── zips/                    # Các file ZIP nộp bài (output.zip, source_code_v4.zip,...)
│   └── builds/                  # Các thư mục submission đã build (submission_turn2,...)
│
├── experiments/                 # Lịch sử thử nghiệm qua các phiên bản (v1.0 đến v6.0)
│   ├── v1.0_baseline_crash_Error/
│   ├── v1.1_format_fix_Pass/
│   ├── v2.0_local_qwen_7b/
│   ├── v3.0 - handmade/
│   ├── v4.0_turn2_cpu/
│   ├── v4.1_score_optimization/
│   ├── v5.0_kaggle_qwen_7b/
│   └── v6.0_colab_pipeline/
│
├── reference_solutions/         # Thư mục chứa bài làm tham khảo từ đồng đội
│   └── DungLe/                  # Solution của DungLe (đạt ~39.31 - 39.36 điểm bxh)
│
├── results/                     # Kết quả đánh giá và log chạy nghiệm thu
│   ├── v4.0_score_38.6974_2026-07-22/
│   ├── v4.1_candidate_2026-07-22/
│   └── v4.1_score_37.7063_2026-07-23/
│
├── outputs/                     # File output tạm / kết quả dự đoán trung gian
├── tmp/                         # Thư mục tạm thời
├── README.md                    # Tài liệu hướng dẫn này
└── requirements.txt             # Danh sách thư viện Python phụ thuộc
```

---

## 🚀 Hướng dẫn Nhanh

* **Đề bài & Thể lệ**: Xem [docs/Problem_Statement.md](file:///d:/Project/Viettel%20AI/docs/Problem_Statement.md).
* **Bài làm Tham khảo tốt nhất**: Xem giải pháp của DungLe tại [reference_solutions/DungLe](file:///d:/Project/Viettel%20AI/reference_solutions/DungLe).
* **Quản lý Submissions**: Xem các file zip đã nộp tại [submissions/zips/](file:///d:/Project/Viettel%20AI/submissions/zips).
