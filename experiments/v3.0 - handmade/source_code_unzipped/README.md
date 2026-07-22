# Viettel AI Race 2026 – vòng 1

Giải pháp baseline suy luận offline cho bài toán nhận diện thực thể y khoa và
chuẩn hóa chẩn đoán/thuốc sang ICD-10-CM và RxNorm.

## Yêu cầu

- Python 3.10 trở lên
- Không cần cài package ngoài, không gọi API và không cần GPU
- Dữ liệu đầu vào có cấu trúc `input/1.txt` đến `input/100.txt`

## Chạy suy luận

```bash
python run.py --input input --output output --zip output.zip
```

Kết quả tạo ra:

```text
output.zip
└── output/
    ├── 1.json
    ├── 2.json
    ├── ...
    └── 100.json
```

Mỗi vị trí ký tự là chỉ số Python zero-based, đầu đóng/mở `[start, end)`. Bộ
suy luận tự kiểm tra rằng `source_text[start:end] == entity["text"]` trước khi
ghi file.

## Kiểm tra bài nộp

```bash
python validate.py output.zip --input input
```

Validator kiểm tra danh sách 100 file, JSON schema, loại thực thể, candidates và
toàn bộ character span.

## Phương pháp

- Từ điển/regex ưu tiên cụm dài nhất để tránh span lồng nhau.
- Nhận diện phủ định và tiền sử theo ngữ cảnh câu/mục.
- Ánh xạ chẩn đoán sang ICD-10-CM và thuốc sang RxNorm.
- Nhận diện tên/kết quả xét nghiệm định lượng và định tính.
- Chạy xác định, tái lập hoàn toàn và không phụ thuộc dữ liệu hoặc dịch vụ ngoài.
