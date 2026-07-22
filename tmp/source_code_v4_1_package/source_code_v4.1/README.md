# Viettel AI Race 2026 - Đề 2 nâng cấp - CPU offline

Pipeline `v4.1` được viết mới cho bộ `input_turn2_vong1.zip`. Pipeline không dùng
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
  --output "..\..\submission_turn2_v4_1_balanced\output" `
  --zip "..\..\output_v4.1_balanced.zip" `
  --profile balanced
```

Hoặc truyền bất kỳ thư mục `input` nào có các file `.txt` tương ứng. Chương
trình ghi JSON vào thư mục `--output` và tạo ZIP có cấu trúc `output/1.json`,
..., `output/100.json`.

## Kiểm tra bài nộp

```powershell
python validate.py "..\..\output_v4.1_balanced.zip" `
  --input "..\..\data\raw\input_turn2_vong1_run\input"
```

Validator kiểm tra danh sách file, UTF-8/JSON, đủ trường, tập nhãn/assertion,
candidate, entity trùng và toàn bộ character span.

Chạy regression test trước khi đóng gói:

```powershell
python -m unittest -v test_regression.py
```

`balanced` là cấu hình nộp khuyến nghị. Cấu hình `precision` có thể tạo bằng
`--profile precision`; cấu hình này loại thêm các khái niệm trong văn bản giáo
dục không có ngữ cảnh bệnh nhân và chỉ nên dùng như một phép thử leaderboard.

Điểm đã ghi nhận của bản `v4.0` ngày 22/07/2026 là `38.6974` (WER `56.5532`,
J_assertion `50.2764`, J_candidates `26.4511`). Không có ground truth theo từng
hồ sơ, vì vậy `v4.1` không tuyên bố tăng điểm trước khi được BTC chấm; validator
chỉ xác nhận tính hợp lệ và khả năng tái lập của bài nộp.

## Phương pháp

- Chuẩn hóa Unicode NFC với bản đồ offset ngược về chuỗi gốc để xử lý cả văn
  bản Unicode tổ hợp (NFD) mà không làm sai vị trí.
- Từ điển y khoa tổng quát ICD-10/RxNorm, ưu tiên cụm dài nhất.
- Regex cho liều thuốc, đường dùng, tên xét nghiệm và kết quả định
  lượng/định tính.
- Mapping theo biệt dược/liều cho các trường hợp RxNorm dễ nhầm giữa ingredient,
  branded drug và strength-specific drug; mapping ICD-10-CM theo ngữ cảnh cho
  các chẩn đoán mơ hồ.
- Sinh hiệu chỉ được xuất khi tên và kết quả liên kết trực tiếp trong cùng cụm,
  tránh bắt nhầm số thể tích/tốc độ truyền dịch.
- Loại các cụm chắc chắn không phải điều trị/chẩn đoán của bệnh nhân như dị ứng
  thuốc, kháng thuốc và danh sách xét nghiệm chỉ được khuyến nghị trong tương lai.
- Scope ngữ cảnh cục bộ và heading để suy luận phủ định, người nhà và tiền sử.
- Chạy xác định, tái lập hoàn toàn, không có bước mạng trong inference.
