# Viettel AI Race 2026 - Đề 2 nâng cấp - CPU offline

Pipeline `v4` được viết mới cho bộ `input_turn2_vong1.zip`. Pipeline không dùng
output của các experiment cũ, không gọi API, không cần GPU và chỉ cần Python
3.10 trở lên.

Pipeline chỉ dùng Python standard library. Toàn bộ tri thức ICD-10/RxNorm cần
cho inference nằm trong `knowledge_base.py`; không có model weights, dịch vụ
mạng hoặc tập dữ liệu phụ phải tải thêm.

## Schema hỗ trợ

- `TRIỆU_CHỨNG`
- `TÊN_XÉT_NGHIỆM`
- `KẾT_QUẢ_XÉT_NGHIỆM`
- `CHẨN_ĐOÁN` với candidate ICD-10
- `THUỐC` với candidate RxNorm
- Assertions: `isNegated`, `isFamily`, `isHistorical`

Mọi span dùng chỉ số ký tự Python dạng `[start, end)` và được kiểm tra bằng
điều kiện `source_text[start:end] == entity["text"]`.

## Chạy

Từ thư mục chứa file này:

```powershell
python run.py `
  --input "..\..\data\raw\input_turn2_vong1_run\input" `
  --output "..\..\submission_turn2_v4\output" `
  --zip "..\..\output.zip"
```

Hoặc truyền bất kỳ thư mục `input` nào có các file `.txt` tương ứng. Chương
trình ghi JSON vào thư mục `--output` và tạo ZIP có cấu trúc `output/1.json`,
..., `output/100.json`.

## Kiểm tra bài nộp

```powershell
python validate.py "..\..\output.zip" `
  --input "..\..\data\raw\input_turn2_vong1_run\input"
```

Validator kiểm tra danh sách file, UTF-8/JSON, đủ trường, tập nhãn/assertion,
candidate, entity trùng và toàn bộ character span.

Lần chạy bàn giao trên 100 hồ sơ đã qua validator với 2.569 entity và không có
file rỗng. Vì không có nhãn ground truth của test, README không tuyên bố điểm
leaderboard; validator chỉ xác nhận tính hợp lệ và khả năng tái lập của bài nộp.

## Phương pháp

- Chuẩn hóa Unicode NFC với bản đồ offset ngược về chuỗi gốc để xử lý cả văn
  bản Unicode tổ hợp (NFD) mà không làm sai vị trí.
- Từ điển y khoa tổng quát ICD-10/RxNorm, ưu tiên cụm dài nhất.
- Regex cho liều thuốc, đường dùng, tên xét nghiệm và kết quả định
  lượng/định tính.
- Scope ngữ cảnh cục bộ và heading để suy luận phủ định, người nhà và tiền sử.
- Chạy xác định, tái lập hoàn toàn, không có bước mạng trong inference.
