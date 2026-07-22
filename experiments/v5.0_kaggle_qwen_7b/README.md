# Viettel AI Race 2026 - Phiên bản V5 (Kaggle Qwen 7B)

Đây là phiên bản nâng cấp từ `v2.0_local_qwen_7b` kết hợp với tính năng ánh xạ (mapping) siêu tốc offline của `v4.0_turn2_cpu`. Script được thiết kế để nộp thẳng lên môi trường Kaggle Notebook (có GPU).

## Đặc điểm nổi bật
- **Trích xuất 5 loại thực thể**: `THUỐC`, `TRIỆU_CHỨNG`, `CHẨN_ĐOÁN`, `TÊN_XÉT_NGHIỆM`, `KẾT_QUẢ_XÉT_NGHIỆM`.
- **Gán nhãn chi tiết (Assertions)**: Hỗ trợ `isHistorical`, `isFamily`, `isNegated`.
- **Offline Mapping Code**: Dùng file `knowledge_base.py` để tìm nhanh ICD-10 và RxNorm offline bằng thuật toán matching, loại bỏ hoàn toàn sự phụ thuộc vào API REST (tránh lỗi Network/Timeout trên Kaggle).
- **Tự động đóng gói**: Sinh thẳng ra file `output.zip` cuối pipeline để submit.

## Cách chạy trên Kaggle

1. Tạo một Notebook mới trên Kaggle, bật tính năng GPU (T4 x2 hoặc P100).
2. Upload file script duy nhất: `run_kaggle_pipeline.py` vào Notebook. Toàn bộ từ điển (knowledge base) đã được nhúng sẵn vào bên trong file này!
3. Import Dataset (File zip `input_turn2_vong1.zip`).
4. Đường dẫn Input đã được cấu hình mặc định là `/kaggle/input/datasets/laxurie/data-main/input` và Output nén thành `/kaggle/working/output.zip`.
5. Mở Terminal hoặc tạo cell chạy lệnh:
   ```bash
   pip install transformers accelerate bitsandbytes
   python run_kaggle_pipeline.py
   ```
6. Đợi script chạy xong và download file `output.zip` từ mục `/kaggle/working/` để submit.
