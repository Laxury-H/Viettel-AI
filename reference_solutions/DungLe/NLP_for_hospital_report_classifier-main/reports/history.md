# Lịch sử tối ưu

Production hiện tại là V21 question-diagnosis pruning, điểm **39.3128**.

Các kết luận còn hiệu lực:

- Correction RxNorm cho `metoprolol 25 mg` có lợi; các nhóm candidate khác đã
  bị loại hoặc không tạo thêm lợi ích xác nhận.
- BamiBERT exact-span gate cho chẩn đoán tăng điểm mạnh từ 38.7600 lên 39.1466.
- Nhóm 56 triệu chứng precision kết hợp với chẩn đoán tăng tiếp lên 39.2864.
- Mở rộng 15 chẩn đoán làm cả WER, assertion và candidate giảm.
- Nhóm 19 triệu chứng recall, boundary replacement và aggressive diagnosis đều
  giảm điểm.
- Qwen hybrid giảm 1.3131 điểm so với control, nên không còn trong production.

V17 thử alias `đỏ mắt`: hai span không overlap, confidence teacher lần lượt
`0.998023` và `0.998120`. Leaderboard đạt **39.2786**, giảm `0.0078`; WER
`55.8911`, J_assertion `50.9040`, J_candidates `26.9369`. Kết luận: loại alias,
không tiếp tục tăng recall triệu chứng theo confidence đơn thuần.

V19 thêm repeated-line consensus để sửa lỗi teacher tách vụn mà không nới
allowlist toàn cục. Câu `Không ghi nhận co giật, cứng đờ, cắn lưỡi hoặc tiểu
tiện không tự chủ.` xuất hiện nguyên văn ở hồ sơ 11 và 40. BamiBERT nhận đúng
toàn span ở hồ sơ 11 (`0.995004`) nhưng chỉ nhận fragment `tiểu tiện` ở hồ sơ
40 (`0.973019`). V19 khôi phục toàn span ở hồ sơ 40 và suy luận lại
`isNegated` theo ngữ cảnh đích. Delta: thêm 1 triệu chứng, không xóa hoặc sửa
thực thể V16.

Leaderboard V19 đạt **39.2901**, tăng `0.0037` so với V16. WER giảm từ
`55.8810` xuống `55.8688`; J_assertion giữ `50.9200`, J_candidates giữ
`26.9369`. Kết luận: promote V19 thành production.

V20 đưa assertion-only ablation lên trên nền V19. Hai chẩn đoán `tăng HA`
trong câu hỏi `có phải là tăng HA thật sự không` được bỏ `isNegated`; không
đổi span, type, candidate hoặc entity count. V18 cũ được thay thế bởi V20 để
mỗi lần nộp luôn kế thừa production tốt nhất đã xác nhận. Leaderboard V20 đạt
đúng **39.2901** với WER `55.8688`, J_assertion `50.9200` và J_candidates
`26.9369`: hoàn toàn trung tính, nên không promote.

V21 kiểm tra hệ quả trực tiếp của V20: vì thay đổi assertion không tác động đến
J_assertion, hai mention `tăng HA` nhiều khả năng không được ghép với gold.
Candidate loại đúng hai chẩn đoán nằm ở vị trí focus của câu hỏi yes/no; không
thay đổi span/type/candidate/assertion nào khác. Đây là quy tắc theo cấu trúc
ngôn ngữ, không hardcode record hoặc offset. Leaderboard V21 đạt **39.3128**,
tăng `0.0227`: WER `55.8487`, J_assertion `50.9613`, J_candidates `26.9477`.
Cả ba thành phần đều tăng, nên V21 được promote.

V22 thử recall có ngữ cảnh trên nền V21. BamiBERT nhận hai exact span
`khó chịu` ở hồ sơ 46 và 97 với confidence `0.997601` và `0.997684`; cả hai
đều nằm trong câu bệnh nhân hiện tại `cảm thấy khó chịu mệt mỏi nhiều`.
Candidate thêm đúng 2 triệu chứng, không sửa hoặc xóa entity production.
Leaderboard chỉ đạt **39.2947**, giảm `0.0181`; WER xấu từ `55.8487` lên
`55.8767`, J_assertion giảm từ `50.9613` xuống `50.9289`, J_candidates giữ
`26.9477`. Kết luận: loại V22 và dừng recall expansion theo confidence đơn
thuần.

V23 thử sửa một lỗi boundary của teacher. Span
`miệng thấy hơi thở mùi khó chịu` (`0.997473`) chứa reporting-prefix
`miệng thấy`; candidate thay bằng `hơi thở mùi khó chịu`. Quy tắc trim áp dụng
theo cấu trúc ngôn ngữ, không theo record hoặc offset. Delta gồm một span thêm
và một span bỏ, entity count giữ nguyên.
