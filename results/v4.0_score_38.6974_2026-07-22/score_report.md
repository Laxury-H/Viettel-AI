# Baseline v4.0 — điểm chính thức 38.6974

## Kết luận kỹ thuật

Bản `v4.0_turn2_cpu` đã được BTC chấm đủ 100/100 bản ghi. Điểm nghẽn lớn nhất là ánh xạ candidate (`26.4511`) vì đây vừa là chỉ số thấp nhất, vừa có trọng số cao nhất (`40%`). Nhận diện text cũng còn yếu: WER `56.5532` tương ứng `text_score = 43.4468`.

## Chỉ số và đóng góp vào điểm cuối

| Thành phần | Chỉ số BTC | Điểm dùng trong công thức | Trọng số | Đóng góp |
|---|---:|---:|---:|---:|
| Text | WER 56.5532 | 43.4468 | 0.3 | 13.03404 |
| Assertions | Jaccard 50.2764 | 50.2764 | 0.3 | 15.08292 |
| Candidates | Jaccard 26.4511 | 26.4511 | 0.4 | 10.58044 |

Phép kiểm tra độc lập:

`0.3 × 43.4468 + 0.3 × 50.2764 + 0.4 × 26.4511 = 38.69742`, làm tròn thành `38.6974`.

## Phạm vi và nguồn dữ liệu

- Cohort: toàn bộ 100 bản ghi trong `input_turn2_vong1.zip`.
- Baseline so sánh: chính bản `output.zip` có SHA-256 `B814014F8A8EE785F28CB6CC6D04D874C27FF6256885C4C9246C964D0E6A26B1`.
- Nguồn chỉ số: ảnh trang kết quả Viettel AI Race do người dùng cung cấp, thời gian nộp hiển thị `22/07/2026 22:32`.
- Không có ground truth hay điểm từng bản ghi, nên mọi chẩn đoán lỗi chi tiết chỉ là giả thuyết cần kiểm chứng bằng lần nộp tiếp theo.

## Hướng nâng cấp có thể kiểm chứng

1. Giảm entity dư và sửa biên span để hạ WER.
2. Chỉ giữ candidate có độ tin cậy cao, đúng ICD-10 cho `CHẨN_ĐOÁN` và RxNorm cho `THUỐC`.
3. Sửa phạm vi `isHistorical`, `isFamily`, `isNegated` ở các trường hợp đã audit được.
4. Đóng gói v4.1 thành artifact riêng; không ghi đè baseline này.

## Giới hạn và kế hoạch đo

Aggregate metrics không xác định được record/khái niệm nào sai. Vì vậy bản v4.1 cần thay đổi có kiểm soát, lưu manifest khác biệt và dùng điểm BTC của lần nộp kế tiếp làm phép thử ngoài mẫu. Nếu có thêm lượt nộp, nên tách ablation candidate và extraction để phân biệt tác động.
