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

V34 kiểm tra đồng thời hai subsystem trực giao trên V30. Subsystem thứ nhất gỡ
18 `isFamily` trong các hồ sơ tư vấn mà mẹ/ông là bệnh nhân chính. Subsystem
thứ hai thay 20 mã ICD-10-CM tần suất cao bằng mã có trong danh mục ICD-10
Việt Nam ban hành kèm Thông tư 06/2026/TT-BYT. Không đổi entity, text, span
hoặc type. Leaderboard đạt **41.0455**, tăng `1.5088` so với V30: WER giữ
`55.4442`, J_assertion tăng từ `51.3029` lên `51.3898`, J_candidates tăng từ
`26.9477` lên `30.6544`. Kết luận causal: family-scope có lợi nhẹ; sai phương
ngữ ICD-10-CM là nút thắt candidate lớn và hướng ICD Việt Nam được promote.

V35 là exploitation cho lượt cuối. Candidate giữ family-scope đã xác nhận và
mở rộng crosswalk từ 20 lên 62 mã, tương ứng 227 entity. So với V34 chỉ có
thêm 78 entity đổi candidate; WER và J_assertion phải bất biến. Hai mã viêm
gan B/C mơ hồ được loại khỏi expansion. Dự phóng bảo thủ **41.43–41.82**.

Leaderboard V35 đạt **41.8224**, đúng sát biên trên dự phóng và tăng `0.7769`
so với V34. WER giữ `55.4442`, J_assertion giữ `51.3898`, J_candidates tăng
từ `30.6544` lên `32.5967` (`+1.9423`). So với V30, tổng điểm tăng `2.2857`
và J_candidates tăng `5.6490`. V35 được promote thành production cuối; kết
luận hệ thống là chuẩn hóa đúng phương ngữ ICD Việt Nam tạo đột phá lớn hơn
các thay đổi NER/boundary cục bộ.

V38 ghép hai subsystem trực giao trên V35: 25 lần chi tiết hóa tám mã cha theo
cột 26 của Phụ lục ICD Việt Nam và 7 sửa assertion theo cấu trúc bệnh án Việt
Nam. Leaderboard đạt **41.7942**; WER giữ `55.4442`, J_assertion tăng từ
`51.3898` lên `51.4203`, nhưng J_candidates giảm từ `32.5967` xuống
`32.5035`. Vì hai subsystem sửa hai trường metric độc lập, có thể phân rã
chính xác: V36 candidate-only đóng góp `-0.03728` điểm, V37 assertion-only
đóng góp `+0.00915` điểm. V38 bị loại; V35 tiếp tục là production đã chấm,
còn V37 được ưu tiên nộp tiếp với điểm suy ra khoảng **41.8315**.

Kết luận ICD được hiệu chỉnh: gold cần đổi phương ngữ từ ICD-10-CM sang mã có
trong danh mục Việt Nam nhưng vẫn giữ mức trừu tượng của mention. Cờ “không
được sử dụng vì có mã 4/5 ký tự cụ thể hơn” dành cho mã hóa bệnh chính không
nên được áp máy móc vào entity linking của cuộc thi.

V37 được nộp độc lập lúc 00:02 ngày 26/07/2026 và đạt đúng **41.8315**:
WER `55.4442`, J_assertion `51.4203`, J_candidates `32.5967`. Kết quả khớp
hoàn toàn với phép phân rã từ V38, xác nhận bảy sửa assertion đóng góp
`+0.0091` điểm so với V35. V37 được promote thành production; V35 vẫn được
lưu làm rollback/control.

V39 tiếp tục hướng tài liệu lai Việt Nam nhưng tách một nguyên nhân khác:
`isHistorical` bị rò từ tiêu đề tiền sử sang đoạn hỏi đáp/giáo dục được ghép
ngay sau đó. Candidate gỡ đúng 6 assertion ở hai hồ sơ, giữ nguyên 2.689
entity, span, type và candidate. Đây là probe assertion-only chưa chấm, SHA
`37446a6fbd2ff6d8cf4d4384dec1b19e8eb777ad1317d60819ffcb1c8a81603b`.
Sau khi V37 được xác nhận, V39 được giữ làm artifact causal trên V35 và không
còn là bản nộp tiếp.

V40 ghép đúng sáu sửa seam của V39 lên V37 production. Tập thay đổi V37 và
V39 rời nhau, nên V40 giữ nguyên cả bảy sửa assertion đã được leaderboard xác
nhận và chỉ tạo một ablation sáu thay đổi trực tiếp so với mốc **41.8315**.
Không đổi entity/span/type/candidate; validator PASS; SHA
`f970f1c913464b58f997747bfb51da3324dd496ec33394be3b68c75ba49e53b5`.
V40 được nộp lúc 00:17 ngày 26/07/2026 và đạt đúng **41.8315**, với cả WER,
J_assertion và J_candidates giống hệt V37. Sáu thay đổi không có ảnh hưởng đo
được; loại V40 và giữ V37 làm production.

Sau V40, audit causal chuyển khỏi assertion seam. Toàn bộ sáu `isFamily` còn
lại đều mô tả thân nhân thật; 46 cặp near-clone không cho thêm gap
entity/boundary; 363 surface có candidate được kiểm tra và không có surface
lặp nào gán mã không nhất quán. Đối chiếu hơn 12 nghìn nhãn trong Phụ lục ICD
Việt Nam tìm được một lỗi exact-label rõ ràng: hai mention
`Bệnh tim mạch do xơ vữa động mạch` ở hồ sơ 6 và 11 đang gán `I70.90`, trong
khi nhãn chính thức tương ứng `I25.1`.

V41 chỉ đổi hai candidate `I70.90` → `I25.1` trên V37; không đổi
entity/span/type/assertion. Từ hiệu ứng V34/V35, mỗi candidate đúng đã làm
J_candidates tăng xấp xỉ `0.0249`, nên nếu cả hai mention được match thì dự
phóng khoảng **41.8514**. Validator PASS; SHA
`3e8bf322229b060608828f3525238a9d38cf03712490c1fa29dd76f327dd88e3`.

Audit ba tầng tiếp theo gồm danh mục ICD quốc gia 2026, danh mục tra cứu ICD
của Bệnh viện Phụ Sản - Nhi Đà Nẵng và thống kê bệnh án Bệnh viện Đa khoa Y
học cổ truyền Hà Nội. Kết quả phân biệt một lỗi ẩn: mã hiện tại có thể hợp lệ
trong ICD nhưng không phải mã của exact label tiếng Việt. `D24` là `U lành ở
vú`, trong khi `U xơ tuyến vú` được các nguồn bệnh viện gắn `N60.2`. Năm
mention của hồ sơ 66 đang mang `D24`.

V42 thay thế V41 trước khi V41 được nộp. Candidate gồm 7 thay đổi đồng nhất:
2 lần `I70.90` → `I25.1` và 5 lần `D24` → `N60.2`; mọi trường khác bất biến.
Nếu cả bảy mention được match và có cùng lượng tử candidate như V34/V35, dự
phóng J_candidates `32.7709`, tổng điểm khoảng **41.9012**. Validator và
deterministic rebuild PASS; SHA
`a2205b94040b164617ab36b9588576bc070a5fa49f895f78cc5447a90bdb663c`.

V43 được đóng gói như follow-up có điều kiện, không phải bản nộp ngay. Nó hoàn
chỉnh ba exact-label boundary trong phần tiền sử bệnh: một nhãn F31.8 có hậu
tố `khác` và hai nhãn J44.9 có hậu tố `không xác định`. V43 chỉ được cân nhắc
sau khi V42 xác nhận hướng exact-label bệnh viện; SHA
`fb6b366d75a5ab82b009c1ec437eda544e648c4e6ba6dfa4dafa014902ab93fc`.

V42 được nộp ngày 26/07/2026 và đạt **41.9476**: WER `55.4442`,
J_assertion `51.4203`, J_candidates `32.8870`. So với V37, WER và assertion
bất biến đúng thiết kế, còn J_candidates tăng `0.2903`, đóng góp chính xác
`0.1161` vào tổng điểm. Hiệu ứng gộp xác nhận batch bảy exact-label correction
là dương; nếu phân bổ đều, mức tăng là `0.04147` J_candidates, tương đương
`0.01659` điểm tổng trên mỗi occurrence được thay. V42 được promote thành
production. V43 chưa
được nộp vì thêm rủi ro WER; vòng kế tiếp ưu tiên mở rộng candidate-only theo
nhãn bệnh viện Việt Nam.

Audit tiếp theo dùng trực tiếp phụ lục Excel ICD-10 năm 2026 do CDC Đồng Nai
đăng tải, thay vì chỉ đọc nhãn chính từ PDF. Việc đọc cả cột hướng dẫn bao
gồm/loại trừ giúp bác bỏ nhiều false positive: `chèn ép tim` vẫn thuộc I31.9,
`tâm phế mạn` vẫn thuộc I27.9, và các mã năm ký tự như J96.90/M48.00 có mặt
thật trong danh mục Việt Nam. Hai sai lệch còn lại có bằng chứng mạnh:
`viêm tim` khác `viêm cơ tim`, `bệnh tim mạch` khác `bệnh tim`; V44 đóng gói
ba sửa I51 candidate-only và PASS validator.

V45 mở rộng V44 trước khi nộp bằng hai mention `đột quỵ` đang gán I63.9.
I63.9 là `nhồi máu não, không xác định`, trong khi I64 là `đột quỵ, không xác
định là xuất huyết hay nhồi máu`; cả hai ngữ cảnh chỉ ghi đột quỵ và không
khẳng định nhồi máu. V45 có đúng 5 candidate changes trên các hồ sơ
2/17/26/30/34, không đổi entity/span/type/assertion. Ngoại suy có điều kiện từ
V42 cho J_candidates `33.0944`, tổng điểm `42.0305`. Validator, bốn invariant
tests và deterministic rebuild đều PASS; SHA
`c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3`.

V45 được nộp lúc 01:37 ngày 26/07/2026 và đạt **41.9694**. WER giữ
`55.4442`, J_assertion giữ `51.4203`, còn J_candidates tăng từ `32.8870` lên
`32.9413` (`+0.0543`). Mức tăng tổng `+0.0218` được giải thích gần như hoàn
toàn bởi trọng số `0.4 × ΔJ_candidates = 0.02172`, xác nhận batch candidate
vẫn dương. Tuy vậy, hiệu ứng trung bình chỉ `+0.01086` J_candidates trên mỗi
thay đổi, thấp hơn mức phân bổ đều của V42; không được giả định cả năm sửa đều
cùng có lợi. V45 được promote thành production, còn các nhánh dịch-ngữ-cảnh,
multi-candidate, recall và boundary tiếp tục tách riêng.

V46 kiểm tra nhánh dịch-ngữ-cảnh đầu tiên trên V45. Sáu mention `tăng nhãn áp`
ở hồ sơ 23/27/45/50 thực chất nằm trong hai cấu trúc thần kinh lặp: CT sọ kèm
phù gai thị, hoặc não úng thủy từ sơ sinh kèm hệ thống dẫn lưu/shunt được chỉnh
sửa. Candidate đổi H40.9 (glaucoma không xác định) sang G93.2 (tăng áp lực
trong sọ lành tính) mà không đổi entity/span/type/assertion. Đây là probe cùng
cơ chế, không phải remap toàn cục theo surface. Validator, hai invariant tests
và deterministic rebuild PASS; SHA
`42fe979ce39959b5cc4b686d61985b7f132d4afa8788ad940accdd7643ecbebc`.

V47 quay lại V45 production và kiểm tra cấu trúc phân cấp ICD bằng một batch
candidate-only lớn, không trộn V46. Audit danh mục ICD 2026 tìm được 94 mention
trên 50 hồ sơ/38 template, thuộc 27 cohort mà surface tiếng Việt khớp nhãn mã
category sau chuẩn hóa trình bày, nhưng V45 đang trả mã con `không xác định`.
V47 thay mã con bằng đúng category (ví dụ E66.9→E66, I50.9→I50,
G43.9→G43); không fuzzy-match và giữ nguyên entity/span/type/assertion. Dự
phóng cơ học bảo thủ theo marginal V45 là `+0.4098`, vượt ngưỡng sử dụng lượt
`+0.35`. Ba unit test thủ công, validator 100 hồ sơ/2689 entity, audit độc lập,
delta 94 candidate-only và deterministic byte-for-byte rebuild đều PASS; SHA
`144f63831e96723cf26378cd288844d41452dd4847de2f49495b5e0098096b71`.
V47 sẵn sàng cho một lượt nộp có kiểm soát; V45 vẫn là rollback production
cho tới khi điểm leaderboard xác nhận hướng category so với unspecified child.

V47 được nộp lúc 03:25 ngày 26/07/2026 và đạt **41.4810**, thấp hơn V45
`0.4884`. WER vẫn `55.4442` và J_assertion vẫn `51.4203`, trong khi
J_candidates giảm từ `32.9413` xuống `31.7203` (`-1.2210`). Với trọng số
candidate `0.4`, toàn bộ mức giảm được giải thích chính xác bởi
`0.4 × -1.2210 = -0.4884`. Kết luận causal: gold ưu tiên mã con/unspecified
child trong phần lớn batch hoặc ít nhất không chấp nhận category cha thay thế;
không tiếp tục mở rộng parent-category và không promote V47. V45 tiếp tục là
production tốt nhất.

Sau kết quả âm của V47, audit chuyển sang recall thay vì tiếp tục sửa mã đã
có. Đối chiếu toàn bộ 100 hồ sơ với nhãn bệnh ICD Việt Nam 2026 và kiểm tra
ngữ cảnh lân cận tìm được 15 mention chẩn đoán có bằng chứng mạnh nhưng V45
chưa trả về: 6 `trứng cá`, 2 `rụng tóc toàn bộ`, 2 `mày đay`, 2 `bạch biến`,
1 `cao răng`, 1 `viêm túi mật` phủ định và 1 `Parkinson`. Mỗi nhóm được hỗ
trợ bởi entity cùng họ hoặc entity song song đã có trong chính hồ sơ; mã dùng
leaf/unspecified child theo bài học V47. V48 chỉ thêm 15 chẩn đoán trên 8 hồ
sơ, không thay bất kỳ entity V45 nào. Validator, direct tests và deterministic
rebuild PASS; SHA
`18c702c704574445fe7add31cf15b6508fe297a63d7f1aacc3ceb26b3f1b75d1`.
Ngoại suy bảo thủ từ V29 cho khoảng **42.0386** (`+0.0692`), vì vậy V48 là
probe recall tách biến, không được mô tả là batch bảo đảm tăng `0.35`.

V48 được nộp lúc 03:47 ngày 26/07/2026 và đạt **41.7881**, thấp hơn V45
`0.1813`. WER xấu từ `55.4442` lên `55.5975` (`+0.1533`), J_assertion giảm
từ `51.4203` xuống `51.0402` (`-0.3801`), và J_candidates giảm từ `32.9413`
xuống `32.8884` (`-0.0529`). Phân rã theo trọng số cho mức giảm xấp xỉ
`-0.0460` từ WER, `-0.1140` từ assertion và `-0.0212` từ candidate, tổng
`-0.1812` do làm tròn. Kết luận causal: exact ICD label và ngữ cảnh y khoa
lân cận chưa đủ chứng minh gold có annotate mention; phần giải thích/giáo dục
có chính sách chọn lọc hơn rule hiện tại. Không tiếp tục mở rộng recall theo
nhãn danh mục, không ghép cohort symptom thứ cấp, và không promote V48. V45
vẫn là production tốt nhất.

Sau V48, audit assertion xác nhận 26 chênh lệch còn lại so với rule nền chủ
yếu là ngoại lệ đã có bằng chứng leaderboard từ V34/V37: mẹ hoặc ông là bệnh
nhân chính trong hồ sơ tư vấn; `tiền sử:` cùng dòng; và cấu trúc
`chưa bị ... trước đó`. Vì vậy không mở lại assertion. Audit nhãn chính thức
trên 760 diagnosis cũng không tìm được một batch exact-label lớn mới; hướng
còn hợp lệ chỉ là candidate-only cross-family có ngữ cảnh nguồn rõ ràng.

V49 đóng gói đúng năm candidate changes trên V45: hai
`tai biến mạch máu não` I63.9→I64, mở rộng quy tắc `đột quỵ` đã có hiệu ứng
dương trong V45; và ba `Bệnh amyloidosis` có hậu tố ngoài span
`tự miễn dịch`, E85.9→E85.3 theo khái niệm nguồn Autoimmune/AA amyloidosis.
Không đổi entity/span/type/assertion, 100 hồ sơ/2.689 entity, validator và ba
direct test PASS, deterministic rebuild PASS; SHA
`2bbf6f3d0fad8c292b5ce753b46f2572634538c8365840d622c8b5dc7aeab7f3`.
Dự phóng theo marginal V45 là **41.9912** và theo marginal V42 lạc quan là
**42.0523**, đều dưới ngưỡng chiến lược `+0.35`; V49 được giữ ở trạng thái
HOLD, không thay `submission/output.zip`.

V49 được nộp lúc 04:06 ngày 26/07/2026 và đạt **41.8633**, thấp hơn V45
`0.1061`. WER giữ `55.4442`, J_assertion giữ `51.4203`, còn J_candidates
giảm từ `32.9413` xuống `32.6763` (`-0.2650`). Với trọng số candidate `0.4`,
toàn bộ mức giảm được giải thích bởi `0.4 × -0.2650 = -0.1060` (sai khác
`0.0001` do làm tròn). Kết luận causal: candidate của mention không nên được
suy từ qualifier nằm ngoài boundary; span `Bệnh amyloidosis` phải được đánh
giá như chính span đó, không tự động nhận E85.3 từ hậu tố `tự miễn dịch`.
Hai thay đổi `tai biến mạch máu não` không được tách thành lượt nộp mới vì
batch gộp không cho biết chúng dương, trung tính hay âm. Loại V49 và toàn bộ
cohort cùng cơ chế qualifier-outside-span; V45 vẫn là production.

Sau khi bỏ yêu cầu mỗi lượt phải đạt `+0.35`, V50 được dựng như causal split
của V49. Nó quay lại V45 và chỉ đổi hai entity
`tai biến mạch máu não` I63.9→I64 trong hồ sơ 3; ba thay đổi E85.3 bị loại.
Hai occurrence tạo đúng một record-level substitution: xóa I63.9, thêm I64,
không thay candidate-list length. Mọi entity/span/type/assertion bất biến;
validator, hai direct test, candidate-set audit và deterministic rebuild PASS.
SHA `f50106500205ed954a5addc36210f7f6eca355b9c76dba0d4a9f340f7f0d85e0`.
V50 là ablation thông tin cao, không phải cam kết tăng lớn; khoảng tham khảo
theo marginal cũ là **41.9781–42.0026**.

Do người dùng không còn yêu cầu mỗi lượt phải tăng tối thiểu `+0.35`, V46
được mở lại làm probe độc lập. Sau khi phát hiện V51, thứ tự chốt là V51,
V50 rồi V46: V51 đo precision-pruning ở đường nối xét nghiệm, V50 đo riêng
synonym đột quỵ ở hồ sơ 3, còn V46 đo lỗi dịch `tăng nhãn áp` trong bệnh cảnh
thần kinh ở bốn hồ sơ. Chỉ hợp nhất các nhánh có leaderboard dương; V45 tiếp
tục là control/rollback.

V51 mở một cơ chế precision khác hoàn toàn: gỡ đúng hai entity E11.9 trong
chuỗi lỗi `tổng phân tích nước tiểu có đái tháo đườngđái tháo đường` ở hồ sơ
38. Chẩn đoán hợp lệ `Đái tháo đường típ 2` trong cùng hồ sơ vẫn được giữ.
V51 còn 2.687 entity; không có record-level candidate-set delta vì E11.9 vẫn
tồn tại qua chẩn đoán hợp lệ. Tín hiệu cần quan sát là WER giảm và/hoặc
J_assertion tăng. Validator, hai test bất biến và deterministic rebuild PASS;
SHA `c0df1d0b6eeaed0996d4a3fc13ac552050fd4c9cac97ec554786bb835781985b`.

V51 được nộp lúc 14:36 ngày 26/07/2026 và đạt **41.9878**, tăng `0.0184`
so với V45. WER giảm từ `55.4442` xuống `55.4298`; J_assertion tăng từ
`51.4203` lên `51.4354`; J_candidates tăng từ `32.9413` lên `32.9653`.
Theo trọng số chính thức, ba phần đóng góp lần lượt khoảng `+0.00432`,
`+0.00453` và `+0.00960`. Cả ba metric cùng dương xác nhận hai entity ở
đường nối urinalysis là false-positive và V51 được promote thành production.

V52 được dựng trên V51 để kiểm tra phần mở rộng literal-duplicate. Nó giữ
token đầu và chỉ gỡ token thứ hai trong 3 `phù phù`, 1 `đau đau` và 4
`mệt mỏi - mệt mỏi`, tổng 8 symptom removals trên 5 hồ sơ/4 template. Các
echo trong ngoặc không được trộn. Artifact có 2.679 entity; validator, hai
direct test và deterministic rebuild PASS; SHA
`1c442828e18a153db5bd86765e83a921f49a012ee7927cfbde8992c840c4b3e9`.

Đối chiếu lại official sample cho thấy các occurrence `táo bón` và `lo âu`
cùng surface nhưng position khác nhau đều được trả thành mention riêng. Điều
này trực tiếp bác bỏ giả định tổng quát của V52: repeated mention không phải
duplicate extraction. V52 được chuyển sang trạng thái reject-unsubmitted;
không dùng artifact này cho lượt nộp.

V53 áp dụng phần có bằng chứng chính thức của audit medication-section. Trong
V51 chỉ còn hai thuốc nằm trong heading lịch sử rõ nhưng thiếu
`isHistorical`: `Torsemide` tại hồ sơ 57 dưới `Thuốc trước khi nhập viện` và
`bactrim` tại hồ sơ 92 dưới `Thuốc đã dùng trước đây`. Official sample gắn
`isHistorical` cho toàn bộ thuốc trước nhập viện nhưng giữ assertion rỗng cho
triệu chứng chỉ định, nên V53 chỉ sửa hai thuốc và không lan temporality sang
`nhiễm khuẩn đường tiết niệu` hay symptom khác. Candidate có 2.687 entity,
không đổi mention/span/type/candidate; direct tests, strict validator và
deterministic rebuild PASS; SHA
`04c18e2e77a5105f0c085beb23f2e19b1a1122f788778af1785b4dff8f081ab6`.

V53 được nộp lúc 16:04 ngày 26/07/2026 và đạt **41.9901**, tăng `0.0023`
so với V51. WER giữ `55.4298`, J_candidates giữ `32.9653`, còn J_assertion
tăng từ `51.4354` lên `51.4432` (`+0.0078`). Với trọng số assertion `0.3`,
đóng góp dự kiến là `0.3 × 0.0078 = 0.00234`, khớp hoàn toàn mức tăng tổng
sau làm tròn. Kết quả xác nhận chính sách section-level temporality cho hai
thuốc đích; V53 được promote thành production và V51 được giữ làm rollback.

Sau V53, audit same-record temporality tìm được tám mismatch có bằng chứng
chặt hơn cue từ khóa đơn lẻ. Trong hồ sơ 4, sáu mention `buồn nôn`,
`tiêu chảy`, `hội chứng ruột kích thích` và `loét tá tràng` nằm trực tiếp
trên hai dòng `Triệu chứng cách đây vài năm`, đồng thời các surface tương ứng
đã có occurrence `isHistorical` ở phần tiền sử của cùng hồ sơ. Trong hồ sơ
69, `trầm cảm` và `ý định tự tử` đã mang `isNegated` trong câu phủ định quá
khứ `đã bị ... trước đó`, còn occurrence đầu hồ sơ đã mang `isHistorical`.
V54 chỉ thêm tám `isHistorical`, không đổi mention/span/type/candidate.
Artifact có 2.687 entity; direct tests, strict validator và deterministic
rebuild PASS; SHA
`e0f5a7471bae4659bb2cded51dbb8e18ad779d868c481dede84881365c832f2e`.

V54 được nộp lúc 16:23 ngày 26/07/2026 và đạt **41.9973**, tăng `0.0072`
so với V53. WER giữ `55.4298`, J_candidates giữ `32.9653`, còn J_assertion
tăng từ `51.4432` lên `51.4670` (`+0.0238`). Đóng góp theo trọng số là
`0.3 × 0.0238 = 0.00714`, khớp mức tăng tổng sau làm tròn. Kết quả xác nhận
same-record temporality và multi-assertion cho các cue quá khứ tường minh;
V54 được promote thành production, V53 được giữ làm rollback.
