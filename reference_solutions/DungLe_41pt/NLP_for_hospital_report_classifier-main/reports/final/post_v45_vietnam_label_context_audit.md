# Audit nhãn Việt Nam theo vai trò ngữ cảnh sau V45

## Kết luận

Giữ nguyên V45 production và **không tạo ZIP mới**. Audit này tìm được một
cụm nhãn ICD có vẻ lớn khi chỉ so khớp từ bề mặt, nhưng sau khi đọc đúng vai
trò diễn ngôn chỉ còn 7 thay đổi candidate-only đủ hợp lý. Mức tăng dự phóng
là `+0.1161` theo biên V42 lạc quan và `+0.0305` theo biên V45 gần nhất, đều
thấp hơn ngưỡng chiến lược `+0.35`.

Artifact production vẫn là `submission/output.zip`, SHA-256:

```text
c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3
```

## Insight chính: cùng một surface không đồng nghĩa cùng một mã

Đối chiếu exact/fuzzy label trên 760 mention `CHẨN_ĐOÁN` ban đầu gợi ý đổi
toàn bộ 21 mention `đái tháo đường`/`tiểu đường` từ E11.9 sang E14.9. Tuy
nhiên, ngữ cảnh chia cụm này thành ba cơ chế khác nhau:

| Vai trò ngữ cảnh | Occurrence | Record | Template | Quyết định |
|---|---:|---:|---:|---|
| Bệnh án lâm sàng ngầm type 2 | 15 | 14 | 11 | Giữ E11.9 |
| Giáo dục/yếu tố nguy cơ tổng quát | 4 | 2 | 2 | E14.9 là ứng viên hợp lý |
| Đường nối dịch máy trong mục nước tiểu | 2 | 1 | 1 | Loại khỏi batch |

15 mention đầu xuất hiện trong bệnh án người lớn với các dấu hiệu như béo
phì, chế độ ăn, bệnh thận mạn hoặc biến chứng thần kinh. Surface ngắn không
nói rõ type nhưng concept nguồn có khả năng là type 2; sửa theo exact label
thuần túy sẽ lặp lại lỗi specificity của V36. Bốn mention trong văn bản giáo
dục chỉ liệt kê yếu tố nguy cơ, nên E14.9 phù hợp hơn với nhãn bệnh viện
`Các thể loại đái tháo đường không xác định (Chưa có biến chứng)`.

Danh mục ICD của Bệnh viện Phụ Sản - Nhi Đà Nẵng hiển thị E14.9 đúng theo
nghĩa trên:

<https://phusannhidanang.org.vn/TraCuuXetNghiem/lstICD/GetICD?page=1104>

## Hai cohort bổ sung đã qua đọc ngữ cảnh

| Surface | Hiện tại | Đề xuất | Occurrence | Lý do |
|---|---|---|---:|---|
| `loãng xương` | M81.0 | M81.9 | 1 | Văn bản chỉ nói thiếu calci, không có hậu mãn kinh |
| `tai biến mạch máu não` | I63.9 | I64 | 2 | Biến cố không nêu rõ nhồi máu |

Danh mục bệnh viện phân biệt M81.0 `Loãng xương sau mãn kinh` với M81.9
`Loãng xương không đặc hiệu`:

<https://phusannhidanang.org.vn/TraCuuXetNghiem/lstICD/GetICD?page=551>

Ba cohort đã review vì thế chỉ có `4 + 1 + 2 = 7` occurrence, nằm trong 3
record và 3 template độc lập.

## Insight về loại tài liệu

Dữ liệu không chỉ là bệnh án cá nhân. Nhiều record là nguyên văn bài giáo dục
sức khỏe hoặc hỏi đáp bệnh viện: một bài Vinmec về thiếu men G6PD và một bài
AloBacsi về bệnh dại khớp rất sát nội dung input. Vì vậy:

- Không được xóa mention chỉ vì nó không mô tả bệnh của người hỏi.
- Assertion và candidate phải theo câu chứa mention, không theo “bệnh chính”
  của toàn document.
- Số lần lặp cao trong bài giáo dục không phải bằng chứng duplicate annotation.

Nguồn đối chiếu:

- <https://www.vinmec.com/vie/bai-viet/thieu-men-g6pd-la-benh-gi-co-nguy-hiem-khong-vi>
- <https://alobacsi.com/dich-vu-y/nuoc-uong-cua-meo-do-vao-vet-xuoc-lieu-co-lay-benh-dai.html>

## Duplicate literal: tín hiệu lỗi dữ liệu, chưa phải sửa an toàn

Audit phát hiện 5 cặp entity cùng surface đứng sát nhau trong 4 record, 3
template:

- 1 cặp chẩn đoán `đái tháo đườngđái tháo đường`;
- 3 cặp triệu chứng `phù phù`;
- 1 cặp triệu chứng `đau đau`;
- tổng type: 1 `CHẨN_ĐOÁN`, 4 `TRIỆU_CHỨNG`.

Raw input cũng chứa chính các token lặp này. Không có gold local để chứng minh
gold chỉ giữ một mention, nên tự động xóa sẽ có rủi ro làm WER và assertion
xấu đi. Chúng chỉ nên được dùng làm marker cho translation seam.

## Kinh tế lượt nộp

Từ leaderboard:

- V42: `+0.1161 / 7 = +0.01659` điểm cho mỗi exact-label correction;
- phần tăng thêm V45: `+0.0218 / 5 = +0.00436` điểm cho mỗi correction.

Với 7 thay đổi mới:

```text
V42 optimistic: 7 × 0.01659 = +0.1161
V45 residual:   7 × 0.00436 = +0.0305
```

Muốn đạt `+0.35` cần ít nhất khoảng 22 thay đổi chất lượng V42 hoặc 81 thay
đổi ở biên V45. Batch hiện tại không đạt quy mô và không nên dùng một lượt
nộp.

## Tái lập

```bash
python3 scripts/analyze_vietnam_label_context_cohorts.py \
  --input input \
  --submission submission/output.zip \
  --output /tmp/vietnam_label_context_audit.json
```

Kết quả chuẩn: 100 record, 69 template; 15/4/2 mention diabetes theo ba vai
trò; 1 osteoporosis; 2 cerebrovascular; 5 duplicate pairs; quyết định
`hold`.
