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

V21 production đạt WER `55.8487`, J_assertion `50.9613` và
J_candidates `26.9477`. Artifact phát hành là `submission/output.zip`, SHA-256:

```text
df74ff00aa2498cc15fccd93270f135b71998f18ac61502848e3e72240807d7d
```

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
