# Lượt nộp 2: Sửa lỗi Format thành công

## Thông tin
- Phương pháp: Giữ nguyên kết quả bóc tách từ `v1.0` (Groq Llama-3-70b).
- Cập nhật: Viết script `format_exact.py` ép toàn bộ các mảng (`candidates`, `assertions`, `position`) nằm trên 1 dòng duy nhất để không làm crash bộ đếm Regex của BTC.
- Kết quả: Máy chủ chấm thi đã quét thành công toàn bộ 100 file, đưa ra điểm số thực sự của mô hình.

## Điểm số
- **Score:** 28.41820
- **WER:** 71.8709
- **J_assertion:** 28.8919
- **J_candidates:** 28.2797
