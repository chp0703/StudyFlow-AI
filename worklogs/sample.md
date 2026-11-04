# Hướng dẫn viết worklog

## Quy ước

- Mỗi thành viên có một file riêng: `worklogs/<github-username>.md` (ví dụ `phkhoiit-1508.md`).
- Mỗi lần làm việc là một mục mới, đặt **mới nhất ở cuối file**.
- Ngày lấy theo ngày tạo PR, định dạng `YYYY-MM-DD`.
- Chỉ ghi việc bạn đã làm; viết ngắn, mỗi ý một gạch đầu dòng.

## Cấu trúc một mục

```markdown
## YYYY-MM-DD — Tên công việc

**Mục tiêu:** một câu nói việc này nhằm đạt điều gì.

**Đã làm**
- Việc 1 (nêu rõ thư mục/file hoặc màn hình liên quan).
- Việc 2.

**Kết quả:** số PR và nhánh (PR #n, `tên-nhánh`), kết quả kiểm tra (build, test).

**Ghi chú**
- Điều chưa kiểm tra, rủi ro hoặc việc còn dang dở.
```

## Lưu ý

- **Mục tiêu:** nói lý do, không lặp lại danh sách việc.
- **Đã làm:** viết theo thứ tự đã làm; dùng tên file/thư mục thật.
- **Kết quả:** chỉ ghi điều đã kiểm chứng được; chưa test thì ghi ở phần Ghi chú.
- **Ghi chú:** bỏ phần này nếu không có gì cần cảnh báo.
