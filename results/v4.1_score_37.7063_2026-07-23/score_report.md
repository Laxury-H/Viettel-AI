# v4.1-balanced — điểm chính thức 37.7063

## Kết luận

Bài `v4.1-balanced` nộp lúc `23/07/2026 00:23` đã được chấm đủ 100 bản ghi và đạt `37.7063`, thấp hơn baseline v4.0 (`38.6974`) là `0.9911` điểm. Phần giảm lớn nhất nằm ở assertions, sau đó là text; candidates gần như đi ngang.

## Chỉ số và đóng góp

| Thành phần | Chỉ số BTC | Điểm dùng trong công thức | Trọng số | Đóng góp |
|---|---:|---:|---:|---:|
| Text | WER 57.5212 | 42.4788 | 0.3 | 12.74364 |
| Assertions | Jaccard 48.0229 | 48.0229 | 0.3 | 14.40687 |
| Candidates | Jaccard 26.3896 | 26.3896 | 0.4 | 10.55584 |

Từ các số hiển thị: `0.3 × 42.4788 + 0.3 × 48.0229 + 0.4 × 26.3896 = 37.70635`, phù hợp với điểm leaderboard sau quy tắc làm tròn nội bộ.

## So với v4.0 đạt 38.6974

| Chỉ số | v4.0 | v4.1 | Thay đổi | Đánh giá |
|---|---:|---:|---:|---|
| Final score | 38.6974 | 37.7063 | -0.9911 | Giảm |
| WER | 56.5532 | 57.5212 | +0.9680 | Xấu hơn |
| Text score | 43.4468 | 42.4788 | -0.9680 | Giảm |
| J_assertion | 50.2764 | 48.0229 | -2.2535 | Giảm mạnh nhất |
| J_candidates | 26.4511 | 26.3896 | -0.0615 | Gần như ngang |

Đóng góp vào phần giảm xấp xỉ: assertions `-0.67605`, text `-0.29040`, candidates `-0.02460`. Vì v4.1 thay đổi nhiều nhóm quy tắc cùng lúc và không có ground truth từng hồ sơ, chưa thể quy nguyên nhân cho một rule cụ thể.

## Quyết định cho bản tiếp theo

- Giữ v4.0 làm baseline tốt nhất đã xác nhận.
- Không dùng v4.1-balanced làm nền mặc định.
- Tạo các ablation nhỏ từ v4.0: assertion-only, boundary/text-only và candidate-only; mỗi lần chỉ thay một nhóm để đo tác động leaderboard.
- Ưu tiên rollback logic assertion của v4.1 vì đây là nguồn giảm điểm lớn nhất.

## Artifact đã lưu

- `output.zip`: chính file v4.1-balanced đã nộp, SHA-256 `8B557D52A7269AD6F3D76E01151EA25802470D8A51E5313D1054114CB6D91F72`.
- `source_code_v4.1.zip`: source tái lập, SHA-256 `9DAAC66E245C4507CD119F900CADBC2AE106438945F976C17E756111E90270C3`.
- `validation.txt`: kết quả kiểm tra 100 JSON, schema và offsets trước khi nộp.
