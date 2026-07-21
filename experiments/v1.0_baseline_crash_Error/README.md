# Lượt nộp 1: API Baseline Crash

## Thông tin
- Phương pháp: Zero-shot Prompting dùng `Groq API` (Llama-3-70b-versatile).
- Thuật toán RxNorm: Exact Match thô sơ qua NLM API.
- Lỗi: Dùng hàm `json.dump` xuất mảng trên nhiều dòng. Hệ thống chấm điểm của BTC dùng Regex quét từng dòng nên bị crash khi parse JSON, dẫn đến kết quả trả về bằng 0.

## Điểm số
- **Score:** 0.36220
- **WER:** 100
- **J_assertion:** 0
- **J_candidates:** ~0.9054%
