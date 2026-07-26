# Chiến lược hai lượt nộp cuối: hệ thống y tế Việt Nam

## Baseline bất biến

V30 là control đã xác nhận:

| Metric | V30 |
|---|---:|
| Score | 39.5367 |
| WER | 55.4442 |
| J_assertion | 51.3029 |
| J_candidates | 26.9477 |

V32 chỉ thêm `isFamily` và giảm `J_assertion` xuống 50.5052. WER và
J_candidates không đổi. Vì vậy gán `isFamily` theo từ khóa thân nhân là một
hướng đã bị leaderboard bác bỏ.

## Insight 1: vai trò bệnh nhân quan trọng hơn từ chỉ quan hệ

Trong văn bản tư vấn sức khỏe Việt Nam, người viết thường hỏi thay cho
`mẹ em`, `ông em`, `bé nhà mình`. Người thân đó là bệnh nhân chính của toàn
văn bản, không phải một sự kiện tiền sử gia đình của bệnh nhân khác.

Subsystem family-scope chỉ gỡ 18 assertion `isFamily` trong ba hồ sơ Q&A
64/80/95. Nó giữ nguyên tiền sử gia đình thực sự, vợ/con là chủ thể thứ cấp,
mọi span, type và candidate.

## Insight 2: codebook đang dùng sai phương ngữ ICD

`knowledge_base.py` tự mô tả mã chẩn đoán là ICD-10-CM. Đề bài chỉ yêu cầu
ICD-10. Phụ lục chính thức của Thông tư 06/2026/TT-BYT dùng danh mục WHO 2019
và có hiệu lực từ 01/07/2026.

Audit V30:

- 761 lượt gán mã chẩn đoán;
- 229 lượt dùng 64 mã không xuất hiện trong phụ lục chính thức Việt Nam;
- 198/761 lượt có phần mở rộng dài kiểu ICD-10-CM;
- candidate hiện gần như toàn singleton, nên reorder/prune danh sách không
  còn là đòn bẩy;
- `J_candidates = 26.9477` đứng yên qua nhiều phiên bản dù NER tốt hơn.

V34 thay 20 mã sai phương ngữ xuất hiện nhiều nhất, tương ứng 149 entity trên
44 hồ sơ. Mỗi mã nguồn đều vắng mặt và mỗi mã đích đều có mặt trong phụ lục
chính thức. Các ví dụ có tần suất cao:

| ICD-10-CM cũ | ICD-10 Việt Nam | Khái niệm | Số entity |
|---|---|---|---:|
| D75.A | D55.0 | Thiếu men G6PD | 18 |
| K29.70 | K29.7 | Viêm dạ dày | 20 |
| H47.10 | H47.1 | Phù gai thị | 12 |
| I25.10 | I25.1 | Bệnh mạch vành do xơ vữa | 11 |
| G43.909 | G43.9 | Migraine không xác định | 9 |
| C92.10 | C92.1 | Bạch cầu dòng tủy mạn | 8 |
| I48.91 | I48.9 | Rung/cuồng nhĩ không xác định | 8 |

## Lượt 1: V34 orthogonal probe

Artifact:

`submission/candidate_v34_v30-vietnam-clinical-orthogonal-probe.zip`

SHA-256:

`8f3915e2dff518e7547f99653129a88c2ea5e73e7e35ff265d77320d608562e4`

V34 thay đổi hai subsystem độc lập:

- 18 assertion family-scope, chỉ có thể làm đổi J_assertion;
- 149 candidate ICD, chỉ có thể làm đổi J_candidates;
- entity, text, span và type giữ nguyên tuyệt đối, nên WER phải bằng 55.4442.

Một lần chấm vì vậy cho hai kết quả A/B riêng biệt.

## Lượt 2: quyết định theo metric, không theo score tổng

| Kết quả V34 so với V30 | Cấu hình V35 cuối |
|---|---|
| J_assertion tăng, J_candidates tăng | giữ family-scope, mở rộng ICD full |
| J_assertion tăng, J_candidates không tăng | giữ family-scope, bỏ ICD |
| J_assertion không tăng, J_candidates tăng | bỏ family-scope, mở rộng ICD full |
| Cả hai không tăng | quay lại V30; dùng lượt cuối cho nhánh WER precision riêng |

Ngưỡng quyết định:

- giữ family-scope khi `J_assertion > 51.3029`;
- mở rộng ICD khi `J_candidates > 26.9477`;
- nếu WER khác `55.4442`, không dùng kết quả vì artifact đã bị sai.

`turn2_v35.py` đã chuẩn bị sẵn sáu cấu hình keep/drop. Chế độ ICD `full`
đổi 62 mã trên 227 entity và cố ý giữ nguyên hai mã B19.1/B19.2 mơ hồ vì một
span đang gộp cả viêm gan B và C mà không có thông tin cấp/mạn.

## Nguồn chuẩn

- Cổng Thông tin điện tử Chính phủ, Thông tư 06/2026/TT-BYT:
  https://vanban.chinhphu.vn/?docid=217536&orggroupid=4&pageid=27160
- Phụ lục danh mục ICD-10 Việt Nam:
  https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf
- WHO ICD-10 Browser 2019:
  https://icd.who.int/browse10/2019/en
