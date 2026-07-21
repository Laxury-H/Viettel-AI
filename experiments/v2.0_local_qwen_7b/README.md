# Lượt nộp 3 (Ngày mai): Local Pipeline (<= 9B)

## Thông tin
- Phương pháp: Inference mô hình `Qwen/Qwen2.5-7B-Instruct` (4-bit quantization). Chạy Local/Colab, tuân thủ 100% luật thi "Không dùng API, Self-host <= 9B".
- Cập nhật: Nâng cấp thuật toán `clean_drug_name` bằng Regex cực mạnh để lột bỏ liều lượng/tần suất/đường dùng ra khỏi tên thuốc trước khi map vào RxNorm API, giúp tăng tỷ lệ hit.
- Formatter: Sử dụng `dump_strict_json` (mảng 1 dòng) đã tích hợp sẵn trong script chính.

## Điểm số
- **Score:** [Điền điểm khi có kết quả]
- **WER:** 
- **J_assertion:** 
- **J_candidates:** 
