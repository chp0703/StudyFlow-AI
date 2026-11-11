# CLAUDE.md — Claude Code Entry Point Adapter (StudyFlow-AI)

@AGENTS.md

---

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Thin adapter để Claude Code tự động nạp cùng bộ quy tắc điều phối với OpenAI Codex từ [`AGENTS.md`](AGENTS.md) |
| **Thẩm quyền (Authority)** | Adapter dẫn chiếu; **không phải nguồn quy tắc độc lập thứ hai**. Mọi quy tắc chính thức nằm tại [`AGENTS.md`](AGENTS.md) và [`docs/team-coordination/`](docs/team-coordination/README.md) |
| **Chủ sở hữu (Owner)** | Project Owner & Repository Governance |
| **Base commit kiểm chứng** | `main` @ `7837050` |

## Chỉ dẫn dành riêng cho Claude Code

1. **Nguồn chỉ dẫn duy nhất:** Dòng `@AGENTS.md` ở đầu file này dùng cú pháp import chuẩn của Claude Code để nạp toàn bộ [`AGENTS.md`](AGENTS.md). Nếu phiên bản hoặc công cụ đọc `CLAUDE.md` hiện tại không tự động mở rộng chỉ thị `@AGENTS.md`, bạn **BẮT BUỘC** đọc trực tiếp file [`AGENTS.md`](AGENTS.md) và [`docs/team-coordination/README.md`](docs/team-coordination/README.md) ngay ở bước đầu tiên trước khi thực hiện bất kỳ thao tác nào.
2. **Xác định vai trò trước khi làm việc:**
   - Kiểm tra xem phiên làm việc hiện tại được giao vai trò nào trong 6 vai trò (`FE-1`, `FE-2`, `BE-1`, `BE-2`, `BE-3`, `BE-4`).
   - Đọc hướng dẫn vai trò tương ứng tại `docs/team-coordination/roles/<ROLE>.md` và kiểm tra quyền sở hữu file tại [`docs/team-coordination/FILE_OWNERSHIP.md`](docs/team-coordination/FILE_OWNERSHIP.md).
3. **Không chạm vào trạng thái nền tảng cá nhân:**
   - File `/CLAUDE.md` ở thư mục gốc được Git theo dõi có chủ đích (qua ngoại lệ `!/CLAUDE.md` trong `.gitignore`) để đồng bộ quy tắc cho cả nhóm.
   - Tuyệt đối không unignore hoặc commit thư mục `.claude/`, `.claude-replay.*`, `history` hoặc các cấu hình phiên cá nhân.
4. **Quy tắc bất biến cần nhớ ngay:**
   - Không sửa, commit, push hoặc merge trực tiếp vào nhánh `main`.
   - Không đưa API key (`DEEPSEEK_API_KEY`), Supabase secret/service-role key, `RPC_SIGNING_SECRET_BASE64`, DB password hoặc `.env` vào code, log, test hay tài liệu.
   - Không tự ý sửa `contracts/` (package `1.0.1 — APPROVED`) hoặc `docs/database/schema_F1.md` (`v1.1`). Mọi thay đổi contract phải tuân theo [`docs/team-coordination/CONTRACT_CHANGE_PROTOCOL.md`](docs/team-coordination/CONTRACT_CHANGE_PROTOCOL.md).
