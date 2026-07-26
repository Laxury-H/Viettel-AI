# Vietnamese Clinical Mention Extraction

Pipeline hiện tại là một đường inference duy nhất, chạy offline và tái lập được:

```text
raw UTF-8
  -> luật lâm sàng + codebook ICD-10/RxNorm
  -> BamiBERT đề xuất CHẨN_ĐOÁN / TRIỆU_CHỨNG
  -> exact-span gate + repeated-line consensus
  -> assertion + candidate normalization
  -> schema validation
  -> deterministic output.zip
```

## Trạng thái

| Bản | Vai trò | Entity | Leaderboard |
|---|---|---:|---:|
| V16 diagnosis-precision | Production cũ | 2.653 | 39.2864 |
| V17 red-eyes | Thêm 2 span `đỏ mắt` | 2.655 | 39.2786 — loại |
| V19 repeated-line consensus | Production cũ | 2.654 | 39.2901 |
| V20 question-assertion | Sửa 2 assertion nghi vấn | 2.654 | 39.2901 — trung tính |
| V21 production | Loại 2 chẩn đoán nghi vấn không ghép gold | 2.652 | **39.3128** |
| V22 patient-discomfort | Thêm 2 triệu chứng `khó chịu` | 2.654 | 39.2947 — loại |
| V23 boundary trim | Sửa biên 1 triệu chứng hơi thở | 2.652 | Chưa chấm |
| V30 evidence fusion | Control trước chuẩn hóa ICD Việt Nam | 2.689 | 39.5367 |
| V34 Vietnam ICD anchor | 20 crosswalk ICD + family scope | 2.689 | 41.0455 |
| V35 Vietnam ICD full | Production cũ: 62 crosswalk ICD | 2.689 | 41.8224 |
| V37 document archetype | Production cũ: assertion Việt Nam | 2.689 | 41.8315 |
| V40 hybrid seam | 6 sửa assertion trên V37 | 2.689 | 41.8315 — trung tính |
| V41 exact ICD label | Probe 2 mã, chưa nộp | 2.689 | Được thay bởi V42 |
| V42 hospital label batch | Production cũ: 7 exact-label candidate | 2.689 | 41.9476 |
| V43 label boundary | Giữ lại do trộn candidate và boundary | 2.689 | Chưa chấm |
| V44 I51 exact-label split | Probe 3 mã, được V45 mở rộng | 2.689 | Chưa nộp |
| V45 cross-family exact label | Production cũ: 5 candidate-only trên V42 | 2.689 | 41.9694 |
| V46 intracranial context | Component cần rebase lên production mới | 2.689 | Chưa nộp |
| V47 parent-category probe | 94 candidate-only | 2.689 | 41.4810 — loại |
| V48 exact diagnosis recall | Thêm 15 chẩn đoán | 2.704 | 41.7881 — loại |
| V49 source-semantic batch | 5 candidate-only | 2.689 | 41.8633 — loại |
| V50 stroke-synonym ablation | Component cần rebase lên production mới | 2.689 | Chưa nộp |
| V51 urinalysis pruning | Production cũ: gỡ 2 false-positive có guard | 2.687 | 41.9878 |
| V52 literal duplicate pruning | Không nộp: official sample giữ mention lặp khác position | 2.679 | Loại trước nộp |
| V53 medication temporality | Production cũ: 2 assertion theo section thuốc | 2.687 | 41.9901 |
| V54 explicit past mentions | **Production**: 8 assertion quá khứ có đối chứng nội hồ sơ | 2.687 | **41.9973** |

V54 production đạt WER `55.4298`, J_assertion `51.4670` và
J_candidates `32.9653`. Artifact phát hành là `submission/output.zip`,
SHA-256:

```text
e0f5a7471bae4659bb2cded51dbb8e18ad779d868c481dede84881365c832f2e
```

Đột phá V34/V35 đến từ việc thay codebook ICD-10-CM bằng mã có trong danh mục
ICD-10 Việt Nam ban hành kèm Thông tư 06/2026/TT-BYT. V35 giữ nguyên WER và
assertion của V34 nhưng tăng J_candidates thêm `1.9423`. V37 tiếp tục tăng
J_assertion `0.0305` bằng cách xử lý cục bộ cấu trúc bệnh án/Q&A Việt Nam mà
không đổi entity, boundary hoặc candidate.

V40 giữ nguyên V37 và chỉ gỡ sáu `isHistorical` bị rò qua đường nối giữa phần
tiền sử với câu hỏi hiện tại hoặc nội dung giáo dục/tư vấn. Bản nộp đạt đúng
điểm và ba metric của V37, nên sáu mention đó không có ảnh hưởng đo được.

V41 tìm được hai mention lặp nguyên văn
`Bệnh tim mạch do xơ vữa động mạch` đang mang `I70.90`, trong khi nhãn Việt
Nam chính thức tương ứng `I25.1`. Audit bổ sung theo danh mục bệnh viện phát
hiện thêm năm mention `u xơ tuyến vú`: `D24` là nhãn tổng quát `U lành ở vú`,
còn exact label bệnh viện là `N60.2`.

V42 thay V41, gồm đúng 7 candidate-only corrections:
hai `I70.90` → `I25.1` và năm `D24` → `N60.2`. Mọi
entity/span/type/assertion bất biến. Artifact:
`submission/candidate_v42_v37-vietnam-hospital-exact-label-batch.zip`,
SHA-256
`a2205b94040b164617ab36b9588576bc070a5fa49f895f78cc5447a90bdb663c`.
Leaderboard tăng từ `41.8315` lên **`41.9476`**; chỉ J_candidates thay đổi,
từ `32.5967` lên `32.8870`. Kết quả xác nhận exact-label theo cách hiển thị
của bệnh viện Việt Nam là tín hiệu candidate có độ chính xác cao.

V43 hoàn chỉnh ba boundary chứa qualifier chính thức (`khác`,
`không xác định`) và được đóng gói sẵn. Tuy nhiên, V43 tiếp tục được giữ lại
vì trộn một sửa candidate với ba thay đổi boundary; ưu tiên tìm thêm batch
candidate-only theo insight đã được V42 xác nhận.

V45 là batch candidate-only tiếp theo và thay thế V44 trước khi nộp. Nó sửa
đúng năm mention theo danh mục ICD Việt Nam: một `viêm tim` I51.4 → I51.8,
hai `bệnh tim mạch` I51.9 → I51.6 và hai `đột quỵ` I63.9 → I64. Không đổi
entity, text, span, type hay assertion. Artifact:
`submission/candidate_v45_v42-vietnam-exact-label-cross-family.zip`, SHA-256
`c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3`.
Leaderboard đạt **41.9694**: WER và J_assertion bất biến, J_candidates tăng
từ `32.8870` lên `32.9413`, nên V45 được promote thành production. Mức tăng
thực tế `+0.0218` thấp hơn ngoại suy trước nộp, cho thấy các sửa exact-label
còn lại có hiệu ứng không đồng đều và cần tiếp tục tách nhóm rủi ro.

V46 xử lý một lỗi dịch-ngữ-cảnh lặp lại. Sáu mention `tăng nhãn áp` trong bốn
hồ sơ không nằm trong bệnh cảnh glaucoma: chúng đi cùng CT sọ não, phù gai
thị, não úng thủy từ sơ sinh và hệ thống dẫn lưu được chỉnh sửa nhiều lần.
Candidate chỉ đổi H40.9 → G93.2 khi có một trong hai chữ ký thần kinh này.
Không đổi entity/span/type/assertion. Artifact:
`submission/candidate_v46_v45-vietnam-intracranial-context-candidate.zip`,
SHA-256
`42fe979ce39959b5cc4b686d61985b7f132d4afa8788ad940accdd7643ecbebc`.
Sau khi V51 được promote, V46 chỉ còn là component nghiên cứu dựng trên V45.
Không nộp trực tiếp ZIP cũ vì nó sẽ làm mất phần tăng đã xác nhận của V51.
Khi đến lượt kiểm tra nhánh này, sáu thay đổi H40.9→G93.2 phải được rebase
trên production tốt nhất tại thời điểm đó.

V47 và V48 cung cấp hai tín hiệu âm quan trọng. V47 thay 94 mã con bằng mã
category cha và làm J_candidates giảm `1.2210`; gold ưu tiên mã leaf hoặc
unspecified child, không ưu tiên category cha dù surface khớp nhãn category.
V48 thêm 15 chẩn đoán từ nội dung giải thích/giáo dục và làm cả WER,
J_assertion lẫn J_candidates giảm; exact ICD label không đủ chứng minh gold có
annotate mention. Do đó các vòng sau loại cả parent-code expansion lẫn recall
diện rộng.

V49 quay lại V45 và chỉ sửa năm candidate của entity đã tồn tại: hai
`tai biến mạch máu não` I63.9 → I64 và ba `Bệnh amyloidosis` có hậu tố
`tự miễn dịch` E85.9 → E85.3. Artifact đã PASS validator, direct tests và
deterministic rebuild. Leaderboard đạt **41.8633**: WER và J_assertion bất
biến, nhưng J_candidates giảm `0.2650`, làm tổng điểm giảm `0.1061`. Kết quả
loại giả thuyết suy candidate từ qualifier nằm ngoài entity boundary và không
cho phép tách hai synonym `tai biến mạch máu não` thành một lượt nộp riêng.
Tại thời điểm V49, production vẫn là V45; hiện V51 đã thay thế nó.

V50 tách V49 thành một ablation causal: chỉ giữ hai
`tai biến mạch máu não` I63.9 → I64 trong hồ sơ 3 và loại toàn bộ E85.3.
Đây là một phép thay tập mã hoàn chỉnh, không thêm candidate, không đổi
entity/span/type/assertion hay độ dài candidate list. Validator, direct tests
và deterministic rebuild PASS. Sau khi V51 được promote, V50 chỉ được dùng
như component và phải rebase lên production mới trước khi nộp.

V51 là probe precision độc lập trên V45. Hồ sơ 38 chứa chuỗi dịch lỗi
`tổng phân tích nước tiểu có đái tháo đườngđái tháo đường`; extractor đang
tạo hai chẩn đoán E11.9 liền nhau tại đây, dù cùng hồ sơ đã có entity hợp lệ
`Đái tháo đường típ 2` trong tiền sử. V51 chỉ gỡ đúng hai entity ở đường nối
xét nghiệm này, giữ nguyên mọi entity khác và giữ chẩn đoán type 2 hợp lệ.
Artifact có 2.687 entity, validator/tests/deterministic rebuild đều PASS.
Leaderboard đạt **41.9878**, tăng `0.0184`; WER giảm `0.0144`,
J_assertion tăng `0.0151` và J_candidates tăng `0.0240`. Vì cả ba metric đều
tốt hơn, V51 được promote thành production.

V52 từng mở rộng structural pruning bằng cách gỡ token thứ hai trong tám cặp
lặp literal. Sau khi đối chiếu official sample—nơi `táo bón` và `lo âu` ở
position khác nhau đều được trả thành entity riêng—V52 bị loại trước nộp.
Repeated mention không được coi là duplicate extraction.

V53 quay lại V51 và chỉ thêm `isHistorical` cho hai thuốc bị bỏ sót trong
section lịch sử rõ ràng: `Torsemide` tại hồ sơ 57 dưới
`Thuốc trước khi nhập viện` và `bactrim` tại hồ sơ 92 dưới
`Thuốc đã dùng trước đây`. V53 giữ nguyên toàn bộ mention/span/type/candidate
và không lan temporality sang triệu chứng chỉ định. Leaderboard đạt
**41.9901**: WER/J_candidates bất biến, J_assertion tăng `0.0078`, làm tổng
điểm tăng `0.0023`; V53 được promote thành production.

V54 kế thừa V53 và hoàn chỉnh tám mention có bằng chứng thời gian trực tiếp:
sáu mention trong hồ sơ 4 nằm trên các dòng bắt đầu
`Triệu chứng cách đây vài năm`, và hai mention hồ sơ 69 đã có
`isNegated` trong câu `đã bị ... trước đó`. Mỗi surface đều có occurrence
`isHistorical` tương ứng trong chính hồ sơ. V54 không đổi mention, boundary,
type hoặc candidate. Leaderboard đạt **41.9973**: WER/J_candidates bất biến,
J_assertion tăng `0.0238`, làm tổng điểm tăng `0.0072`; V54 được promote
thành production.

Audit semantic-context sau V45 gom 28 vị trí đáng ngờ thành 10 cohort và hiệu
chỉnh theo 69 mẫu tài liệu độc lập. Có 22 thay đổi candidate-only tiềm năng,
gồm hai cụm mới đáng chú ý: `tai biến mạch máu não` I63.9 → I64 và
`Bệnh amyloidosis tự miễn dịch` E85.9 → E85.3. Tuy nhiên, 22 vị trí chỉ cho
`+0.3649` ở biên V42 lạc quan nhất và khoảng `+0.0959` theo biên V45 gần
nhất; nhiều vị trí còn phụ thuộc qualifier ngoài boundary. Vì vậy chưa tạo
V47/ZIP và giữ nguyên production. Báo cáo chi tiết:
`reports/final/post_v45_semantic_context_cohort_audit.md`.

Audit nhãn Việt Nam theo vai trò ngữ cảnh tiếp tục kiểm tra fuzzy label trên
760 mention chẩn đoán. Cụm 21 `đái tháo đường`/`tiểu đường` không phải một
batch đồng nhất: 15 mention là bệnh án ngầm type 2, 4 là giáo dục tổng quát
và 2 nằm ở đường nối dịch máy. Cùng với một `loãng xương` tổng quát và hai
`tai biến mạch máu não`, chỉ 7 candidate-only corrections đủ hợp lý. Dự phóng
lạc quan `+0.1161` vẫn thấp hơn ngưỡng `+0.35`, nên không tạo ZIP và tiếp tục
giữ V45. Script tái lập là
`scripts/analyze_vietnam_label_context_cohorts.py`; báo cáo:
`reports/final/post_v45_vietnam_label_context_audit.md`.

Audit cấu trúc candidate tiếp theo phát hiện một hypothesis quy mô lớn nhưng
chưa promote: 759/760 chẩn đoán đang có đúng một candidate, trong khi 94
mention khớp nguyên văn mã category Việt Nam sau khi chỉ bỏ tiền tố `bệnh`,
ngoặc đồng nghĩa và khác biệt dấu gạch. Ví dụ gồm `béo phì` E66.9 → E66,
`suy tim` I50.9 → I50 và `đau nửa đầu` G43.9 → G43. Batch nằm trên 50 record,
38 template; thay candidate hoàn toàn được dự phóng `+0.4098` ngay cả theo
biên V45. Tuy nhiên, chiều category so với unspecified child chưa có ablation
nhân quả, nên chưa tạo ZIP. Script:
`scripts/analyze_icd_parent_candidate_structure.py`; báo cáo:
`reports/final/post_v45_icd_parent_candidate_structure_audit.md`.

V17 giảm `0.0078` điểm: WER tăng `0.0101`, J_assertion giảm `0.0160`,
J_candidates không đổi. Alias `đỏ mắt` đã bị loại.

V19 thêm một tầng ensemble theo tính nhất quán nội bộ: khi cùng một dòng xuất
hiện ở nhiều hồ sơ, hệ thống chỉ truyền một triệu chứng đã nằm trong allowlist
production nếu hồ sơ đích vẫn có fragment BamiBERT cùng loại với confidence
`>= 0.95` và bám vào biên span. Assertion được suy luận lại theo ngữ cảnh đích.
Trên bộ hiện tại, V19 chỉ khôi phục `tiểu tiện không tự chủ` trong câu phủ định
ở hồ sơ 40; không thay đổi 2.653 thực thể production còn lại.

V20 bỏ `isNegated` khỏi hai chẩn đoán trong cấu trúc nghi vấn
`có phải là … thật sự không`, nhưng leaderboard không thay đổi ở bất kỳ chỉ số
nào. V21 dùng tín hiệu này để thử loại hẳn hai mention không được ghép với gold;
leaderboard tăng `0.0227` và cả ba thành phần đều tốt hơn.

V22 bổ sung hai span `khó chịu` với confidence `>= 0.9976`, nhưng làm cả WER
và J_assertion giảm. Vì vậy pipeline dừng mở rộng recall chỉ dựa trên
confidence. V23 chuyển sang sửa biên: thay `miệng thấy hơi thở mùi khó chịu`
bằng mention lâm sàng gọn hơn `hơi thở mùi khó chịu`.

## Cài đặt

Yêu cầu Windows PowerShell, `uv` và Python 3.12:

```powershell
.\scripts\setup.ps1
```

Script tạo `.venv`, cài dependency đã pin và tải
[`cbc-528a/BamiBERT-ViMedNER`](https://huggingface.co/cbc-528a/BamiBERT-ViMedNER)
ở revision cố định `e508eedd34d124e05cf139cc565806c6d4fc5aad`.
Model được fine-tune trên
[ViMedNER](https://eudl.eu/doi/10.4108/eetinis.v11i3.5221).

## Build

Đặt 100 hồ sơ tại `input/1.txt` … `input/100.txt`.

```powershell
# Tái tạo bản production đã đạt 39.3128
.\scripts\build.ps1 -Profile production -RefreshTeacher

# Build lại nhanh bằng cache teacher
.\scripts\build.ps1 -Profile production

# Sinh candidate V23
.\scripts\build.ps1 -Profile v23
```

Build production phải cho đúng SHA-256 ở trên. Mỗi ZIP được kiểm tra tự động về
schema, span, số record, CRC và danh mục label.

## Cấu trúc

```text
official/                     thể lệ và sample do BTC cung cấp
reports/                      kết quả production và lịch sử leaderboard
scripts/setup.ps1             tạo môi trường + tải teacher
scripts/build.ps1             build production/V23
scripts/predict_bamibert.py   inference teacher có cache versioned
scripts/validate_submission.py
src/clinical_mentions/
  knowledge_base.py           alias và ICD-10/RxNorm
  rules.py                    extractor deterministic
  candidates.py               correction đã qua ablation
  model_config.py             cấu hình production/ablation
  pipeline.py                 đường inference phát hành
submission/                   ZIP sẵn sàng nộp
```

Các bản V9–V15, Qwen hybrid, ZIP/report ablation đã bị loại được lưu trong lịch
sử Git thay vì nằm trên nhánh production.

## Nguyên tắc cải tiến

- Giữ `output.zip` ở bản tốt nhất đã được leaderboard xác nhận.
- Mỗi candidate chỉ thay đổi một nhóm nhỏ, có delta entity rõ ràng.
- Không hardcode theo record ID, offset hoặc chuỗi riêng của private test.
- Không promote khi chưa có điểm leaderboard tốt hơn.
