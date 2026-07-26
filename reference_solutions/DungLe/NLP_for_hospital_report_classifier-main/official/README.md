# Official artifacts

- `round1_rules.md`: các ràng buộc đã trích từ thể lệ do người dùng cung cấp.
- `sample_output.json`: ví dụ output chính thức.

Hai file này là bằng chứng đầu vào và không được pipeline sửa đổi. Repo chưa có
gold label, evaluator chính thức hoặc train/dev annotation; vì vậy validator
local chỉ kiểm tra schema, span và package, không thể thay leaderboard.
