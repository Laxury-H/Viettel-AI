# Viettel AI Race 2026 — báo cáo nâng cấp v4.1

## Kết luận

Bản `v4.0` đã chấm được lưu nguyên trạng với điểm **38.6974**. Bản
`v4.1-balanced` là ứng viên mới đã qua validator và kiểm tra dựng lại từ source
ZIP, nhưng **chưa được leaderboard chấm**, vì vậy không được xem là đã tăng
điểm cho đến khi có kết quả từ BTC.

## Baseline đã chấm

| Chỉ số | Giá trị |
|---|---:|
| Final score | 38.6974 |
| WER | 56.5532 |
| Text score = 100 − WER | 43.4468 |
| J_assertion | 50.2764 |
| J_candidates | 26.4511 |

Kiểm tra công thức:

`0.3 × 43.4468 + 0.3 × 50.2764 + 0.4 × 26.4511 = 38.69742`, làm tròn thành
`38.6974`.

## Thay đổi trong v4.1-balanced

- Sửa 68 mapping candidate trên cùng span/type, tập trung vào RxNorm theo biệt
  dược/liều và ICD-10-CM theo ngữ cảnh.
- Thay các span triệu chứng ngắn bằng cụm dài hơn; chuyển `đau nửa đầu` sang
  triệu chứng nếu không có ngữ cảnh chẩn đoán rõ.
- Loại các false positive từ `hạ sốt`, `chống nôn`, `thuốc chống trầm cảm`, dị
  ứng thuốc, kháng thuốc và xét nghiệm mới chỉ được khuyến nghị.
- Bổ sung sinh hiệu theo cặp tên–kết quả, với regex chặt để không bắt nhầm
  `tĩnh mạch 750cc` hoặc tốc độ truyền dịch.
- Sửa scope `isFamily`/`isHistorical` theo chủ thể và episode; thêm phủ định cho
  kết luận hình ảnh có `xác suất thấp`.
- So với v4.0: thêm 145 entity, bỏ 132 entity, 68 candidate change và 84
  assertion change trên các entity giữ nguyên span/type.

## Thống kê đầu ra mới

| Loại | Số entity |
|---|---:|
| TRIỆU_CHỨNG | 1,017 |
| CHẨN_ĐOÁN | 705 |
| TÊN_XÉT_NGHIỆM | 427 |
| KẾT_QUẢ_XÉT_NGHIỆM | 218 |
| THUỐC | 215 |
| **Tổng** | **2,582** |

Assertions: `isHistorical=411`, `isFamily=39`, `isNegated=108`. Có 920 entity
chứa candidates với tổng 925 candidate values.

## Kiểm chứng kỹ thuật

- ZIP có đúng 100 file từ `output/1.json` đến `output/100.json`.
- Mọi JSON đúng schema nâng cấp; không có hồ sơ rỗng và mọi character offset
  thỏa `source[start:end] == text`.
- 16 regression tests đều qua.
- Source ZIP được giải nén vào thư mục sạch và chạy lại trên CPU: 100/100 JSON
  trùng SHA-256 với bản bàn giao.
- Pipeline chỉ dùng Python standard library, không dùng API, model ngoài hoặc
  GPU.

## Giới hạn và bước tiếp theo

Không có ground truth theo record nên chưa thể định lượng mức tăng của v4.1.
Không dựng biểu đồ xu hướng vì mới chỉ có một lần chấm aggregate, không có chuỗi
thời gian hay breakdown theo hồ sơ. Nên nộp `output_v4.1_balanced.zip`, lưu ảnh
kết quả mới, rồi dùng thay đổi của ba thành phần WER/J_assertion/J_candidates để
quyết định vòng tối ưu kế tiếp.
