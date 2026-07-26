# V9.0 — Recall Breakthrough

Nâng cấp trên nền bài **41.9973 điểm** (`reference_solutions/DungLe_41pt/.../submission/output.zip`).

---

## 1. Phát hiện nền tảng: hàm chấm điểm thật sự hoạt động thế nào

Công thức đầy đủ nằm ở **trang 5 của `docs/AI Race 2026 - Cuộc đua AI cho kỹ sư Việt Nam.pdf`**
(bản `docs/Problem_Statement.md` đã bị cắt mất phần này):

```
final_score      = 0.3·text_score + 0.3·assertions_score + 0.4·candidates_score

text_score       = (1/len(test))·Σ_i (1 − WER(i))
assertions_score = (1/len(test))·Σ_i J_assertions(i)
candidates_score = Σ_i J_cand(i)·w_i / Σ_i w_i        với w_i = Σ_{k∈i}(len(gold_candidates(k))+1)

J_X(i) = 1  nếu gold rỗng VÀ prediction rỗng
J_X(i) = 0  nếu gold rỗng VÀ prediction khác rỗng
J_X(i) = |gold ∩ pred| / |gold ∪ pred|  trong các trường hợp còn lại
```

### Hệ quả 1 — chấm điểm là MACRO theo tài liệu
`text_score` và `assertions_score` chia đều cho `len(test)`. **Mỗi file JSON đóng góp đúng 1% điểm,
bất kể nó có 2 hay 74 khái niệm.** Một khái niệm đúng thêm vào tài liệu nghèo đáng giá gấp nhiều lần
thêm vào tài liệu dày.

### Hệ quả 2 — `candidates_score` chỉ phản ứng với MÃ
Đây là phát hiện đắt giá nhất, và nó được kiểm chứng bằng dữ liệu thật chứ không phải suy luận:

| Bản nộp | WER | J_assertion | **J_candidates** |
|---|---:|---:|---:|
| V17-consensus-boundary-94       | 55.8547 | 50.8650 | **26.9369** |
| V17-consensus-boundary-985-single | 55.8046 | 50.9200 | **26.9369** |

Diff hai zip này cho thấy chúng **khác nhau 54 thực thể trên 22 tài liệu**, đủ để làm đổi cả WER lẫn
J_assertion — nhưng `J_candidates` **giống hệt nhau tới từng chữ số**. Cả 54 thực thể đó đều là
`TRIỆU_CHỨNG` (không mang mã), và tập mã của cả 100 tài liệu không đổi.

> **Kết luận: thêm TRIỆU_CHỨNG / TÊN_XÉT_NGHIỆM / KẾT_QUẢ_XÉT_NGHIỆM KHÔNG cải thiện được
> `candidates_score` — chỉ CHẨN_ĐOÁN và THUỐC (mang mã) mới tác động tới metric trọng số 0.4.**

Điều này bác bỏ giả thuyết hấp dẫn "mỗi triệu chứng đúng được Jaccard 1.0 miễn phí".

### Hệ quả 3 — điểm hòa vốn khi thêm khái niệm
Chỉ `text_score` (hòa vốn ~0.50 vì chèn/xóa đối xứng trong WER) và `assertions_score` (~0.36) hưởng
lợi từ khái niệm không mang mã. Trọng số gộp lại cho **ngưỡng hòa vốn ≈ 0.5**: một khái niệm thêm vào
cần khoảng trên 50% khả năng có mặt trong đáp án thì mới đáng giữ.

Đây chính là lý do V48 (thêm 15 thực thể) từng **mất 0.1813 điểm**.

---

## 2. Chẩn đoán: nút thắt nằm ở đâu

Bài nền có 2687 khái niệm (26.9/hồ sơ). Từ ràng buộc `J_assertion = m·a` với `a ≤ 1` suy ra tỉ lệ
khớp `m ≥ 0.515`, tương ứng **đáp án có khoảng 3600–4500 khái niệm (36–45/hồ sơ)**.

Pipeline V7/V8 trước đó **không tự trích xuất gì cả** — nó nạp thẳng `output.zip` của bài nền làm
"teacher spans" rồi chỉ chỉnh lại vài mã. Đối chiếu `output_v8` với bài nền: 90/100 file giống hệt,
10 file còn lại khác đúng 15 khái niệm và **chỉ khác ở trường `candidates`**. Đó là trần điểm.

Độ phủ cũng cực kỳ lệch: doc 46 có 63 khái niệm trong khi doc 48 chỉ có 2 — mà theo chấm MACRO thì
hai file này đóng góp điểm ngang nhau.

---

## 3. Kiến trúc V9

```
input/N.txt ─┐
             ├─► normalize_baseline  (2687 khái niệm nền, BẤT BIẾN TUYỆT ĐỐI)
output.zip ──┘            │
                          ▼
                    Matcher (lexicon_v9.json)
                    · cụm dài thắng cụm ngắn, không chồng lấn
                    · dò cả biến thể NFC lẫn NFD
                    · chặn vùng đã bị baseline chiếm
                          │
                          ▼
                    infer_assertions   (dè dặt — mặc định rỗng)
                          │
                          ▼
                    output/N.json + output.zip
```

| File | Vai trò |
|---|---|
| `build_lexicon.py` | Gộp entry thô → kiểm duyệt → `src/lexicon_v9.json` |
| `src/engine_v9.py` | So khớp từ điển, hợp nhất với bài nền |
| `src/assertions_v9.py` | Suy luận `isNegated` / `isHistorical` cho khái niệm mới |
| `run_v9.py` | CLI: sinh output + đóng gói zip |
| `validate_v9.py` | Kiểm tra 10 ràng buộc chặn nộp + 5 cảnh báo |
| `simulate_score.py` | Mô phỏng điểm theo công thức chính thức, tìm ngưỡng hòa vốn |
| `build_all.py` | Dựng lại toàn bộ từ đầu, cả hai biến thể |

Toàn bộ chạy **100% offline trên CPU**, không gọi API, không nạp model — từ điển là tài nguyên tĩnh.

---

## 4. Ba bug thật đã được phát hiện và sửa

### 4.1 Lệch offset do chuẩn hóa Unicode
`unicodedata.normalize("NFC", text)` **làm đổi độ dài chuỗi** trên **20/100 hồ sơ** ở dạng tổ hợp
(NFD). Mọi offset trả về đều lệch, sinh ra span cắt ngang từ như `' do cào ho'`, `'ộ C\n'`, `'g các '`.

Sửa: `_fold()` chỉ dùng `str.lower()` (đã assert giữ nguyên độ dài trên toàn corpus), còn từ điển thì
dò cả biến thể NFC lẫn NFD. Kết quả: 49 cảnh báo → 6.

### 4.2 Ranh giới âm tiết tiếng Việt
Tiếng Việt viết rời từng âm tiết nên một âm tiết đứng lẻ vẫn thỏa điều kiện ranh giới từ **ngay cả
khi nằm giữa một từ ghép**: `"mạch"` khớp bên trong `"tĩnh mạch"`, `"tim mạch"`, `"động mạch vành"`;
`"nang"` khớp trong `"nang lông"`. Mỗi lần như vậy vừa sai span vừa sai nhãn → bị phạt kép.

Sửa: bề mặt mới bắt buộc có ≥2 âm tiết, trừ một allowlist viết tắt lâm sàng (`ct`, `mri`, `ast`…).

### 4.3 `isHistorical` rò rỉ theo section
Quy tắc "cả vùng dưới heading tiền sử đều là isHistorical" khiến các mục *Triệu chứng hiện tại*,
*Khám lúc vào viện* phía sau cũng bị đóng dấu, trong khi bài nền để rỗng cho chính các khái niệm cùng
câu. Vì 81.6% khái niệm của đáp án có assertions rỗng, luật rò rỉ này **làm tụt điểm**.

Sửa: gỡ hẳn quy tắc section; `isHistorical` chỉ phát khi có cue tường minh sát ngay trước mention, và
không bao giờ phát cùng lúc với `isNegated`.

Ngoài ra `isFamily` bị **vô hiệu hóa hoàn toàn** cho khái niệm mới: lần thử gán theo từ chỉ quan hệ
(V32) từng mất 0.2393 điểm, và bài nền chỉ dùng nhãn này 6/2687 lần.

---

## 5. Kết quả

| | bài nền | v9-conservative | v9-full |
|---|---:|---:|---:|
| Khái niệm | 2687 | 2962 (+275) | 3144 (+457) |
| Khái niệm/hồ sơ | 26.9 | 29.6 | 31.4 |
| Assertions rỗng | 81.6% | 83.1% | 83.7% |
| isFamily | 6 | 6 | 6 |
| Lỗi chặn nộp | — | **0** | **0** |
| Offset sai | — | **0** | **0** |
| Khái niệm nền bị mất/sửa | — | **0 / 0** | **0 / 0** |

**Zero-regression tuyệt đối:** cả 2687 khái niệm của bài 41.9973 điểm được giữ nguyên từng ký tự,
không đổi một `assertion` hay `candidate` nào. Mọi thay đổi đều là bổ sung thuần túy.

---

## 6. Cách chạy

```bash
python build_all.py          # dựng lại từ đầu cả hai biến thể + kiểm tra
python validate_v9.py        # kiểm tra riêng output_v9
python simulate_score.py --baseline _baseline --candidate output_v9
```

---

## 7. Khuyến nghị nộp bài

Không có ground truth nên **không thể biết chắc phía nào của ngưỡng hòa vốn 0.5**. Vòng thẩm định đối
kháng ước lượng precision của khái niệm mới khoảng 55% *trước* khi lọc, và bản hiện tại đã loại 117
bề mặt bị bác cùng 46 bề mặt đơn âm tiết. Cách duy nhất để biết là đo trên leaderboard:

1. Nộp **v9-conservative** trước — thay đổi ít nhất, rủi ro thấp nhất.
2. Đọc phân rã WER / J_assertion / J_candidates, so với `41.9973 / 55.4298 / 51.4670 / 32.9653`.
3. Nếu dương, nộp tiếp **v9-full**; nếu âm, dấu hiệu là đáp án thưa hơn ước lượng → quay về bài nền.

**Mỗi lượt nộp chỉ nên mang một giả thuyết.** Lịch sử dự án cho thấy gộp nhiều thay đổi vào một lượt
(v4.1) làm mất 0.9911 điểm mà không quy kết được nguyên nhân.

### Hướng còn bỏ ngỏ có đòn bẩy lớn nhất
`candidates_score` (trọng số 0.4) đang ở 32.97 — thấp nhất trong ba chỉ số. Vì nó chỉ phản ứng với
**tập mã cấp tài liệu**, đòn bẩy nằm ở việc trích thêm CHẨN_ĐOÁN/THUỐC kèm mã đúng, chứ không phải
thêm triệu chứng. Nếu mô hình "Jaccard trên tập mã" đúng thì ngưỡng hòa vốn cho việc thêm một mã chỉ
khoảng **0.23**, tức là rất đáng để đoán mã thay vì bỏ trống — nhưng điều này chưa phân định được dứt
điểm với mô hình "trung bình theo từng khái niệm mang mã", nên V9 chỉ gán mã cho khái niệm **chưa có
mã** (an toàn dưới cả hai mô hình) chứ không thêm mã thứ hai vào khái niệm đã có mã.
