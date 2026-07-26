# V35 Vietnam ICD full exploitation

## Tín hiệu V34

| Metric | V30 | V34 | Delta |
|---|---:|---:|---:|
| Score | 39.5367 | 41.0455 | +1.5088 |
| WER | 55.4442 | 55.4442 | 0 |
| J_assertion | 51.3029 | 51.3898 | +0.0869 |
| J_candidates | 26.9477 | 30.6544 | +3.7067 |

Theo công thức `0.3*(100-WER) + 0.3*J_assertion + 0.4*J_candidates`,
family-scope đóng góp khoảng `+0.0261` điểm và nhóm ICD Việt Nam đóng góp
`+1.4827` điểm. Hai subsystem đều được giữ.

## V35

V35 mở rộng từ 20 lên 62 mã nguồn vắng mặt trong Phụ lục ICD-10 Việt Nam.
Mọi mã đích đều xuất hiện trong phụ lục chính thức.

- 227 entity đổi candidate so với V30;
- thêm 78 entity đổi candidate so với V34;
- không đổi entity, text, span, type hoặc assertion so với V34;
- giữ nguyên hai mã B19.1/B19.2 vì một span gộp viêm gan B/C và không có
  thông tin cấp/mạn;
- dùng mã Việt Nam cụ thể theo ngữ cảnh cho `S06.30`, `M10.90` và `T14.20`.

Nếu 78 thay đổi mới đạt 50–100% hiệu suất trung bình của nhóm V34, dự phóng
J_candidates tăng thêm khoảng `0.97–1.94`, tương ứng score **41.43–41.82**.

## Kết quả leaderboard

| Metric | V34 | V35 | Delta |
|---|---:|---:|---:|
| Score | 41.0455 | 41.8224 | +0.7769 |
| WER | 55.4442 | 55.4442 | 0 |
| J_assertion | 51.3898 | 51.3898 | 0 |
| J_candidates | 30.6544 | 32.5967 | +1.9423 |

Kết quả nằm đúng sát biên trên dự phóng. V35 được promote thành production.

## Artifact

`submission/candidate_v35_v30-vietnam-icd-full-final.zip`

SHA-256:

`a49ef79d427915d2c3679a96fdcddc8e1454c67e0e44d1562d9e72fbf35777c6`
