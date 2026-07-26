# Submission

- `output.zip`: V45 production, đã chấm **41.9694** (WER `55.4442`,
  J_assertion `51.4203`, J_candidates `32.9413`), SHA-256
  `c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3`.
- `candidate_v23_symptom-boundary-trim.zip`: V23 boundary ablation, chưa chấm.
- `candidate_v24_xlmr-additive-85-pruned.zip`: V19 tốt nhất sau khi loại nhóm
  `đỏ mắt`; đã chấm **39.3762** (WER 55.7062, J_assertion 51.0299,
  J_candidates 26.9477).
- `candidate_v25_v24-symptom-boundary-trim.zip`: kế thừa V24 và sửa đúng một
  boundary `miệng thấy hơi thở mùi khó chịu` → `hơi thở mùi khó chịu`; đã
  chấm **39.3762**, hoàn toàn trung tính ở cả ba metric.
- `candidate_v26_v24-stable-boundary-group.zip`: kế thừa V24 và ghép năm
  boundary expansion stable đã có bằng chứng aggregate `+0.0041`; dự phóng
  **39.3803**, chưa chấm.
- `candidate_v27_v26-semantic-boundary-repeated-recall.zip`: batch lớn gồm 11
  semantic boundary expansion và một repeated-line addition trên V26; tổng 17
  thay đổi so với V24, target **39.386–39.400**, chưa chấm.
- `candidate_v28_v27-repeated-neurologic-recall.zip`: thêm tám symptom trong
  các dòng thần kinh lặp nguyên văn; tổng 25 thay đổi so với V24; đã chấm
  **39.4461** (WER 55.5927, J_assertion 51.1496, J_candidates 26.9477) và
  hiện là control tốt nhất.
- `candidate_v29_v28-high-evidence-recall.zip`: thêm tám symptom có bằng chứng
  accepted-surface/teacher-lexicon trên V28; đã chấm **39.4830** (WER
  55.5478, J_assertion 51.2278, J_candidates 26.9477) và hiện là control tốt
  nhất.
- `candidate_v30_v29-evidence-fusion.zip`: ghép 15 accepted-boundary, 11
  symptom safe, 3 diagnosis safe và 5 sửa candidate top-1 trên V29; đã chấm
  **39.5367** (WER 55.4442, J_assertion 51.3029, J_candidates 26.9477) và
  hiện là control tốt nhất.
- `candidate_v31_v30-semantic-boundary-context-recall.zip`: hoàn chỉnh 34
  boundary theo vị trí/tính chất/bộ phận cơ thể, thêm 7 symptom theo ngữ cảnh
  và sửa một trường hợp câu hỏi không chắc chắn bị hiểu nhầm là phủ định; đã
  chấm **39.4604** (WER 55.5456, J_assertion 51.1501, J_candidates 26.9477),
  thấp hơn V30 nên bị loại.
- `candidate_v32_v30-direct-family-assertion.zip`: quay lại V30 và chỉ sửa 8
  `isFamily` có chủ thể thân nhân trực tiếp; không đổi entity, span, type hoặc
  candidate; đã chấm **39.2974** (WER 55.4442, J_assertion 50.5052,
  J_candidates 26.9477), thấp hơn V30 nên bị loại.
- `candidate_v33_v30-primary-patient-family-scope.zip`: quay lại V30 và gỡ 18
  `isFamily` trong ba hồ sơ hỏi đáp mà mẹ/ông là bệnh nhân chính; vẫn giữ
  `isFamily` cho tiền sử gia đình, vợ trong bệnh sử và nguy cơ di truyền ở
  con; không đổi entity, span, type hoặc candidate; target **39.60–39.78**,
  chưa chấm.
- `candidate_v34_v30-vietnam-clinical-orthogonal-probe.zip`: lượt thử hệ thống
  trên V30, đồng thời gỡ 18 `isFamily` của bệnh nhân chính trong Q&A và thay
  20 mã ICD-10-CM tần suất cao bằng mã có trong Phụ lục Thông tư
  06/2026/TT-BYT. Tổng 149 entity đổi candidate trên 44 hồ sơ; text/span/type
  giữ nguyên. Đã chấm **41.0455** (WER `55.4442`, J_assertion `51.3898`,
  J_candidates `30.6544`), tăng `+1.5088` so với V30 và xác nhận cả hai
  subsystem. SHA-256
  `8f3915e2dff518e7547f99653129a88c2ea5e73e7e35ff265d77320d608562e4`;
  hiện là control tốt nhất.
- `candidate_v35_v30-vietnam-icd-full-final.zip`: lượt cuối mở rộng V34 từ 20
  lên 62 crosswalk ICD Việt Nam, tổng 227 entity đổi candidate; giữ 18 sửa
  family-scope đã được xác nhận. So với V34 chỉ có thêm 78 entity đổi
  candidate, mọi assertion/text/span/type bất biến. Hai mã B19.1/B19.2 được
  giữ lại vì span đang gộp viêm gan B và C nhưng không cho biết cấp/mạn.
  Đã chấm **41.8224** (WER `55.4442`, J_assertion `51.3898`, J_candidates
  `32.5967`), tăng `+0.7769` so với V34 và `+2.2857` so với V30. SHA-256
  `a49ef79d427915d2c3679a96fdcddc8e1454c67e0e44d1562d9e72fbf35777c6`;
  đã promote thành `output.zip`.
- `candidate_v36_v35-vietnam-icd-specificity-probe.zip`: chi tiết hóa 25
  candidate thuộc tám mã cha bị đánh dấu ở cột 26 của Phụ lục ICD Việt Nam.
  Hiệu ứng candidate được phân rã từ V38 là âm: J_candidates `-0.0932`, tương
  đương khoảng `-0.0373` điểm tổng. Không nộp/promote.
- `candidate_v37_v35-vietnam-document-archetype-assertion-probe.zip`: sửa 7
  assertion cho `tiền sử:` viết cùng dòng, tiền sử bản thân phủ định, nhiễm
  trùng đã điều trị và nhãn family-history trong nội dung giáo dục. V38 xác
  nhận subsystem này tăng J_assertion `+0.0305`, tương đương `+0.00915` điểm;
  bản nộp độc lập ngày 26/07 xác nhận đúng **41.8315** và đã được promote
  thành `output.zip`.
- `candidate_v38_v35-vietnam-icd-and-document-archetype.zip`: hợp trực giao
  V36+V37, đã chấm **41.7942** (WER `55.4442`, J_assertion `51.4203`,
  J_candidates `32.5035`), SHA-256
  `1bf8beb6bb7001dd263ece2a6f41dead452f9208956658337e4f4ec8b38c29a1`.
  Bị loại vì phần mã chi tiết làm mất nhiều hơn phần assertion tăng.
- `candidate_v39_v35-hybrid-document-seam-assertion-probe.zip`: probe
  assertion-only trên V35, gỡ 6 `isHistorical` bị rò qua đường nối giữa các
  tài liệu con: câu hỏi hiện tại, giáo dục chung và lời khuyên chung bị đặt
  sau tiêu đề tiền sử. Không đổi entity/span/type/candidate; validator PASS;
  SHA-256
  `37446a6fbd2ff6d8cf4d4384dec1b19e8eb777ad1317d60819ffcb1c8a81603b`.
  Đây là artifact causal lưu trữ trên V35, không nộp vì đã được thay thế bởi
  V40.
- `candidate_v40_v37-hybrid-document-seam-assertion-probe.zip`: candidate kế
  thừa trực tiếp V37 production. Ghép đúng 6 sửa seam của V39 lên V37, trong
  khi giữ nguyên cả 7 sửa đã được xác nhận của V37; không đổi
  entity/span/type/candidate. Đã chấm đúng **41.8315**, mọi metric bằng V37,
  nên bị loại là trung tính. Validator PASS; SHA-256
  `f970f1c913464b58f997747bfb51da3324dd496ec33394be3b68c75ba49e53b5`.
- `candidate_v41_v37-vietnam-icd-exact-label-correction.zip`: candidate kế
  thừa trực tiếp V37 production. Chỉ đổi hai candidate lặp trong hồ sơ 6 và
  11 từ `I70.90` sang `I25.1` cho exact label
  `Bệnh tim mạch do xơ vữa động mạch`; mọi entity/span/type/assertion bất
  biến. Validator PASS; SHA-256
  `3e8bf322229b060608828f3525238a9d38cf03712490c1fa29dd76f327dd88e3`.
  Chưa nộp và đã được V42 thay thế.
- `candidate_v42_v37-vietnam-hospital-exact-label-batch.zip`: kế thừa hai sửa
  của V41 và bổ sung năm exact label
  `u xơ tuyến vú` từ `D24` sang `N60.2`, đúng danh mục ICD hiển thị tại bệnh
  viện và thống kê bệnh án bệnh viện Việt Nam. Tổng cộng 7 candidate changes;
  entity/span/type/assertion bất biến. Đã chấm **41.9476**: WER và
  J_assertion giữ nguyên, J_candidates tăng `+0.2903`, đưa tổng điểm tăng
  `+0.1161`. Đã promote thành `output.zip`. Validator PASS; SHA-256
  `a2205b94040b164617ab36b9588576bc070a5fa49f895f78cc5447a90bdb663c`.
- `candidate_v43_v42-vietnam-official-label-boundary-completion.zip`: follow-up
  đóng gói sẵn nhưng tiếp tục giữ lại do có thay đổi boundary. Hoàn chỉnh một nhãn
  `rối loạn cảm xúc lưỡng cực khác` (`F31.8`) và hai nhãn COPD có qualifier
  `không xác định`; 3 span changes, 1 candidate change. Validator PASS;
  SHA-256
  `fb6b366d75a5ab82b009c1ec437eda544e648c4e6ba6dfa4dafa014902ab93fc`.
- `candidate_v44_v42-vietnam-i51-exact-label-split.zip`: probe candidate-only
  gồm một `viêm tim` I51.4 → I51.8 và hai `bệnh tim mạch` I51.9 → I51.6.
  Validator và deterministic rebuild PASS; SHA-256
  `e2238328e67340810363eff74b5d19988c49ecbe01002b267c0f9f2ed69c7bf0`.
  Chưa nộp và đã được V45 mở rộng.
- `candidate_v45_v42-vietnam-exact-label-cross-family.zip`: kế thừa ba sửa
  I51 của V44 và bổ sung hai `đột quỵ` I63.9 →
  I64; tổng 5 candidate changes trên V42 production, không đổi
  entity/span/type/assertion. Đã chấm **41.9694**, J_candidates tăng `0.0543`
  và tổng điểm tăng `0.0218`; đã promote thành `output.zip`. Validator và
  deterministic rebuild PASS; SHA-256
  `c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3`.
- `candidate_v46_v45-vietnam-intracranial-context-candidate.zip`: **probe
  candidate-only tiếp theo**. Sáu surface `tăng nhãn áp` trong bốn hồ sơ có
  ngữ cảnh CT sọ/phù gai thị hoặc não úng thủy sơ sinh/dẫn lưu não thất được
  đổi H40.9 → G93.2. Mọi entity/span/type/assertion bất biến. Dự phóng có
  điều kiện từ hiệu ứng V45 là J_candidates `33.0065`, tổng điểm `41.9956`.
  Validator và deterministic rebuild PASS; SHA-256
  `42fe979ce39959b5cc4b686d61985b7f132d4afa8788ad940accdd7643ecbebc`.
- `candidate_v47_v45-vietnam-icd-canonical-category-label.zip`: probe đã chấm
  **41.4810** trên V45. Chỉ thay 94 candidate thuộc
  27 cohort/50 hồ sơ khi surface tiếng Việt khớp nhãn category ICD chính thức
  sau chuẩn hóa trình bày (Unicode/case, tiền tố `bệnh`, synonym trong ngoặc
  và dấu gạch); không fuzzy-match và không đổi entity/span/type/assertion.
  Validator, audit độc lập, delta 94/94 và deterministic byte-for-byte rebuild
  PASS; SHA-256
  `144f63831e96723cf26378cd288844d41452dd4847de2f49495b5e0098096b71`.
  WER/J_assertion giữ nguyên nhưng J_candidates giảm `1.2210`, làm tổng điểm
  giảm `0.4884`; bác bỏ chiến lược thay unspecified child bằng category cha.
  Bản bị loại và `output.zip` tiếp tục giữ V45.
- `candidate_v51_v45-urinalysis-translation-pruning.zip`: gỡ đúng hai
  diagnosis E11.9 khỏi seam dịch lỗi urinalysis trong hồ sơ 38, vẫn giữ chẩn
  đoán `Đái tháo đường típ 2`. Đã chấm **41.9878**, cả WER, J_assertion và
  J_candidates đều tốt lên; đã promote thành `output.zip`.
- `candidate_v52_v51-literal-duplicate-symptom-pruning.zip`: artifact nghiên
  cứu đã dựng nhưng **không nộp**. Official sample trả riêng các mention cùng
  surface ở position khác nhau, nên việc xóa `mệt mỏi - mệt mỏi` và các token
  lặp chưa có đủ bằng chứng.
- `candidate_v53_v51-explicit-medication-section-temporality.zip`: ứng viên
  assertion-only trên V51. Chỉ thêm `isHistorical` cho `Torsemide` hồ sơ 57
  dưới `Thuốc trước khi nhập viện` và `bactrim` hồ sơ 92 dưới
  `Thuốc đã dùng trước đây`. Giữ nguyên 2.687 mention, mọi
  text/span/type/candidate và assertion ngoài hai đích. Strict validator,
  direct tests và deterministic rebuild PASS; SHA-256
  `04c18e2e77a5105f0c085beb23f2e19b1a1122f788778af1785b4dff8f081ab6`.
  Đã chấm **41.9901**: WER/J_candidates bất biến, J_assertion tăng
  `+0.0078`, tổng điểm tăng `+0.0023`; đã promote thành `output.zip`.
- `candidate_v54_v53-explicit-past-mention-temporality.zip`: assertion-only
  trên V53. Thêm `isHistorical` cho sáu mention dưới cue nguyên văn
  `Triệu chứng cách đây vài năm` ở hồ sơ 4 và giữ `isNegated` khi bổ sung
  `isHistorical` cho hai mention quá khứ bị phủ định ở hồ sơ 69. Mọi
  mention/span/type/candidate khác bất biến; strict validator, direct tests và
  deterministic rebuild PASS. SHA-256
  `e0f5a7471bae4659bb2cded51dbb8e18ad779d868c481dede84881365c832f2e`.
  Đã chấm **41.9973**: WER/J_candidates bất biến, J_assertion tăng
  `+0.0238`, tổng điểm tăng `+0.0072`; đã promote thành `output.zip`.

Mỗi ZIP chứa đúng `output/1.json` … `output/100.json`.

`output.zip` luôn trỏ tới artifact leaderboard tốt nhất đã được xác nhận.
