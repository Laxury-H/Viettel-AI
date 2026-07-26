# Nhật ký tối ưu Turn 2 — 2026-07-23

## Control đã xác nhận

- D2-V9: 2.569 entity.
- Score: **38.6974**.
- WER: 56.5532; J_assertion: 50.2764; J_candidates: 26.4511.
- SHA-256: `081bf8b2ccb538e93273573fffc22c4e42ebe39b0dcf58a0f29634a9791a56ba`.

## Candidate D2-V10 balanced

- 2.582 entity; schema/span/CRC/allowlist PASS.
- So với control: giữ 2.437 span+type; thêm 145; bỏ 132.
- Thêm/bỏ nổi bật: +48 kết quả xét nghiệm, +48 tên xét nghiệm, bỏ 26 chẩn
  đoán và 4 thuốc bị xem là không thuộc ngữ cảnh bệnh nhân.
- 84 entity giữ nguyên span+type nhưng thay assertion; 68 entity đổi candidate.
- Chưa có gold/leaderboard score, vì vậy đây là A/B candidate chứ không phải
  bản thay thế control.

## Kết quả upstream v4.1

- Upstream `v4.1_score_optimization` đã được chấm **37.7063**.
- WER 57.5212; J_assertion 48.0229; J_candidates 26.3896.
- So với control: tổng -0.9911; text -0.9680; assertion -2.2535; candidate
  -0.0615. Vì nhiều nhóm luật thay đổi cùng lúc, kết quả này không chứng minh
  riêng từng thay đổi tốt/xấu, nhưng đủ để không dùng v4.1 làm bản chính.

## Candidate D2-V11 CPU

- Nền: D2-V9 đã chấm 38.6974.
- Giữ nguyên 2.569 entity, mọi span/type/assertion và thứ tự output.
- Chỉ 14 thực thể thuốc thay candidate RxNorm theo tên + hàm lượng/đường dùng.
- Các mã được đối chiếu với mẫu chính thức và RxNorm API của NLM; inference
  vẫn hoàn toàn offline, không gọi API.
- Validator PASS; SHA-256:
  `d63d002dbc9407d524a28c407f321a637c769150ae45028c529ca6be5d09d7d4`.
- Leaderboard: **38.6887**; WER 56.5532; J_assertion 50.2764;
  J_candidates 26.4295.
- So với control: WER và assertion giữ nguyên đúng thiết kế; J_candidates
  giảm 0.0216 làm tổng điểm giảm khoảng 0.0087. Không promote V11.

## Candidate D2-V12 CPU

V12 tách 14 thay đổi của V11 thành ba ablation không giao nhau; cả ba vẫn giữ
nguyên 2.569 entity và mọi trường ngoài `candidates`.

- `generic`: 7 thay đổi generic SCD, ứng viên nộp đầu tiên; SHA-256
  `53676d123091011c890d41d8927b01c1ca4073f1b5eff39506f9df21320b2bfb`.
- `brand`: 3 thay đổi branded SBD; SHA-256
  `d8ca15ef8065079a63cf9d3c3920f9d609d939a8abe9db6fbab5dc4c48c88893`.
- `component`: 4 thay đổi strength component; SHA-256
  `4f9957c268cd2adbd5f08c1bd6c8fcf8ded16e033d54720c5658a875b5e8be1a`.

Kết quả Generic: **38.7389**; WER 56.5532; J_assertion 50.2764;
J_candidates 26.5550. So với control, J_candidates tăng 0.1039 và tổng điểm
tăng khoảng 0.0415. Đây là bản tốt nhất hiện tại.

V11 gộp cả ba nhóm giảm khoảng 0.0087 trong khi riêng Generic tăng 0.0415, nên
Brand + Component kết hợp có tác động âm khoảng 0.0502. Component đã được nộp
riêng để xác định nguồn giảm.

Kết quả Component: **38.6472**; WER 56.5532; J_assertion 50.2764;
J_candidates 26.3256. So với control, J_candidates giảm 0.1255 và tổng giảm
khoảng 0.0502; loại toàn bộ nhóm Component.

Ba số J_candidates thỏa đúng:
`delta(V11) = delta(Generic) + delta(Component)`, nên đóng góp ròng suy ra của
Brand là `0.0000` ở cấp nhóm. Brand chưa được chấm trực tiếp và không được ưu
tiên vì không thể nâng bản Generic nếu tác động ròng bằng 0.

## Candidate D2-V13 CPU

V13 tách nhóm Generic đang dương thành:

- `core`: 4 thay đổi — metoprolol x2, omeprazole và furosemide; SHA-256
  `c03ade29b71ba021b27eb0a8384055ea67336dd82409d161b8e7b61e3be15ea3`.
- `uncertain`: 3 thay đổi — metoclopramide x2 và Tylenol; SHA-256
  `dcbad34446087655de7cda7f3b08157d894f6c75dad21857c468d5dbdb607f5b`.

Cả hai giữ nguyên mọi trường ngoài candidate. Nộp Core trước: nếu Core vượt
38.7389 thì loại Uncertain; nếu Core nằm giữa control và Generic thì giữ V12
Generic; nếu Core thấp hơn control thì nộp Uncertain.

Kết quả Core: **38.7600**; WER 56.5532; J_assertion 50.2764;
J_candidates 26.6078. Core tăng 0.0626 so với control và 0.0211 so với
Generic, vì vậy Uncertain có đóng góp âm khoảng 0.0211 và bị loại.

## Candidate D2-V14 CPU

V14 tách bốn thay đổi Core thành ba rule độc lập:

- `metoprolol`: 2 entity; SHA-256
  `736b695b7e45248388481de8f40ddfa5b1dc939d3b5bdf411eb3ae17bafce608`.
- `omeprazole`: 1 entity; SHA-256
  `58ed27395281c1a29ac151540b9381811d8f8d326dddd6ef00fab7127552afad`.
- `furosemide`: 1 entity; SHA-256
  `51d55f8f696933e10284f1907dae56e5692ee2070dc4f8565b2b12178559ceb4`.

Nộp metoprolol trước. Nếu nó vượt Core thì loại hai rule còn lại; nếu nó nằm
giữa control và Core thì Core vẫn là cấu hình tốt nhất ở thời điểm đó; nếu nó
thấp hơn control thì phần tăng của Core đến từ omeprazole/furosemide.

## Candidate Qwen hybrid

- Primary: Qwen3.5-9B chạy `--language-model-only` và non-thinking mode.
- Fallback: Qwen3-8B-AWQ khi cần 4-bit chính thức/giới hạn chặt hơn.
- Model chỉ đề xuất exact quote/type; offset, assertion, candidate allowlist,
  merge và validation do mã deterministic quyết định.
- Model proposal không được đè lên entity luật; diagnosis/medication không ánh
  xạ được candidate đóng sẽ bị loại.
- Leaderboard: **37.3843**; WER 58.0204; J_assertion 47.4136;
  J_candidates 26.4159.
- So với control: tổng -1.3131; giảm chủ yếu ở assertion (-2.8628) và text
  (WER xấu hơn 1.4672). Không promote Qwen.

## Quy tắc quyết định

Chỉ promote candidate nếu leaderboard cải thiện score tổng mà không làm một
thành phần suy giảm bất thường. Không thêm rule theo ID hồ sơ hoặc chuỗi riêng
của private test; thay đổi phải là quy tắc lâm sàng tổng quát hoặc học từ model.

## Candidate D2-V17 consensus

- Train `ViPubMedDeBERTa-xsmall` seed 42 với effective batch 32, early stopping
  theo strict F1 gộp đúng hai nhãn `ten_benh` và `trieu_chung_benh`.
- Checkpoint epoch 11 đạt target F1 0.7367 trên dev và 0.7460 trên test; đối
  chứng BamiBERT đạt lần lượt 0.7504 và 0.7541.
- Exact-span consensus hai kiến trúc đạt F1 0.7644 dev và 0.7751 test khi đánh
  giá bằng sliding window, cao hơn từng teacher riêng lẻ.
- Pipeline `boundary-94` tăng F1 so với V16 là +0.05925 dev và +0.05116 test;
  thay 32 span biên ngắn bằng 32 span được hai model đồng thuận.
- ZIP 100 hồ sơ, 2.653 entity, validator PASS; SHA-256
  `71681c1e413e59308eb3bf9f31626ec9dbdbeddb292176cdaaf284676c1cc500`.
- Public control cần vượt: **39.2864**. Chỉ promote V17 sau khi điểm public cao
  hơn control.
- `boundary-94` đạt **39.2778**: WER tốt hơn 0.0263 nhưng J_assertion giảm
  0.0550 do hai boundary mới gộp hai cặp entity phủ định. Không promote.
- `boundary-94-single` không cho một span mới thay đồng thời nhiều entity cũ,
  khôi phục số `isNegated` từ 118 về 120; offline delta vẫn dương +0.05881 dev
  và +0.05116 test. Validator PASS; SHA-256
  `2b995a64897f230e24fde4679904721fe8aad9e18b79d0da841b61deb0c9b86c`.
- `boundary-94-single-causal` còn gắn `isNegated` cho cấu trúc phủ định trực
  tiếp “không/chưa gây/làm + triệu chứng”, đưa tổng `isNegated` lên 121.
  Validator PASS; SHA-256
  `70f3cc736a3ae6408ab435206f50a4490355b1073574659de0fa7795567e4224`.
- Kết quả `boundary-94-single-causal`: **39.2658**; WER 55.8752;
  J_assertion 50.8453; J_candidates 26.9369. Rule causal làm J_assertion giảm
  thêm 0.0197 so với `boundary-94`, nên bị loại.
- `boundary-9875` chỉ thay bốn biên có đồng thuận mạnh nhất, giữ nguyên toàn bộ
  assertion/candidate. Kết quả: **39.3053**; WER 55.8181; J_assertion 50.9200;
  J_candidates 26.9369. Promote.
- `boundary-985-single` thêm đúng một biên `Nôn` thành `Nôn mửa`. Kết quả:
  **39.3094**; WER 55.8046; J_assertion 50.9200; J_candidates 26.9369.
  Đây là cấu hình public tốt nhất.
- `boundary-98-single-stable` thêm quy tắc tổng quát không hấp thụ modifier
  tăng/giảm đứng trước một triệu chứng đã có. Cấu hình đạt delta F1 +0.02546
  trên ViMedNER dev và +0.02592 trên test, validator PASS, 10/10 test PASS;
  SHA-256 `79caaa60bdd06e9897b797333ff265bc4bce7dfdf9e2f05383b7d4378a05d5b3`.
  Public score **39.3094**, bằng bản tốt nhất nên không promote.
- Sau 5 lượt ngày 24/07/2026, đội SOL-GPT đứng hạng **13** với **39.3094**.
  Mốc hạng 10 là 39.7649, còn cách 0.4555 điểm.
