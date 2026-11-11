# AGENTS.md — Quy tắc Điều phối Chung cho AI Coding Agents (StudyFlow-AI)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Điểm vào bắt buộc (Global Entry Point) cho mọi phiên làm việc của OpenAI Codex, Claude Code và các AI coding agents trong repository `StudyFlow-AI` |
| **Thẩm quyền (Authority)** | Quy tắc vận hành cấp repository; dẫn chiếu trực tiếp đến bộ contract chính thức `1.0.1` và logical schema `F1 v1.1` |
| **Chủ sở hữu (Owner)** | Project Owner & Repository Governance (`BE-4` điều phối kỹ thuật) |
| **Base commit kiểm chứng** | `main` @ `7837050` (`Merge pull request #21 from chp0703/feat/f1-frontend-integration`) |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Bối cảnh dự án & Phạm vi hiện tại

- **Dự án:** **StudyFlow-AI** — Hệ thống hỗ trợ lập kế hoạch học tập học thuật có kiểm soát dành cho sinh viên.
- **Phạm vi hiện tại:** Chỉ triển khai **F1 (Intelligent Academic Planner)**. Các tính năng **F2** (Assessment & Adaptive Revision) và **F3** (Daily AI Learning) nằm ngoài phạm vi thực thi của agent trừ khi có quyết định mới được duyệt chính thức.
- **Mô hình phối hợp:** Dự án vận hành với **6 vai trò AI coding độc lập**:
  - **Team Frontend (Claude Code hoặc Codex):** `FE-1` (Task / Planner / Calendar / Confirmation), `FE-2` (Personalized Working Time / Upload Review / Assistant).
  - **Team Backend (Codex):** `BE-1` (Database / Task Schema / Timezone / Working Time), `BE-2` (Scheduler / Proposal / Approval), `BE-3` (AI / DeepSeek / File Ingestion), `BE-4` (Chat / Task Draft / API Integration Coordinator).
- **Nguyên tắc cốt lõi:** Đầu ra của LLM và nội dung tệp tải lên là **dữ liệu không tin cậy (untrusted)**. Mọi thao tác ghi nghiệp vụ chỉ được commit sau khi có quyết định phê duyệt rõ ràng (`explicit user approval`), kiểm chứng quyền sở hữu (`auth.uid()`) và kiểm tra lại tính hợp lệ tại thời điểm duyệt (`approval-time revalidation`).

---

## 2. Đọc trước khi viết code (Read Before Coding)

Trước khi sửa bất kỳ file nào, agent **BẮT BUỘC** đọc theo thứ tự sau:

1. **Bộ điều phối nhóm (`docs/team-coordination/`):**
   - [docs/team-coordination/README.md](docs/team-coordination/README.md) — Điểm vào và hướng dẫn sử dụng bộ điều phối.
   - [docs/team-coordination/PROJECT_SOURCE_OF_TRUTH.md](docs/team-coordination/PROJECT_SOURCE_OF_TRUTH.md) — Thứ tự ưu tiên nguồn sự thật, bảng phân xử mâu thuẫn tài liệu, phân biệt `APPROVED` vs `PROPOSED`.
   - [docs/team-coordination/ARCHITECTURE_AND_RUNTIME_RULES.md](docs/team-coordination/ARCHITECTURE_AND_RUNTIME_RULES.md) — Bản đồ runtime thực tế tại `main` (`7837050`), ranh giới tầng và các kết nối bị cấm.
   - [docs/team-coordination/FILE_OWNERSHIP.md](docs/team-coordination/FILE_OWNERSHIP.md) — Ma trận quyền sở hữu file/module cho 6 vai trò và quy tắc co-review.
   - [docs/team-coordination/INTEGRATION_PROTOCOL.md](docs/team-coordination/INTEGRATION_PROTOCOL.md) — Quy trình branch, worktree, PR, thứ tự tích hợp và bàn giao.
   - [docs/team-coordination/TASK_BOARD.md](docs/team-coordination/TASK_BOARD.md) — Danh mục công việc, trạng thái thực tế và đồ thị phụ thuộc (DAG).
   - [docs/team-coordination/PRODUCT_REQUIREMENTS_AND_DECISIONS.md](docs/team-coordination/PRODUCT_REQUIREMENTS_AND_DECISIONS.md) & [docs/team-coordination/OPEN_DECISIONS.md](docs/team-coordination/OPEN_DECISIONS.md) — Các yêu cầu F1 mới của người dùng và các điểm chờ quyết định.
2. **Hướng dẫn vai trò được giao (đọc đúng role của phiên hiện tại):**
   - [FE-1](docs/team-coordination/roles/FE-1.md) · [FE-2](docs/team-coordination/roles/FE-2.md) · [BE-1](docs/team-coordination/roles/BE-1.md) · [BE-2](docs/team-coordination/roles/BE-2.md) · [BE-3](docs/team-coordination/roles/BE-3.md) · [BE-4](docs/team-coordination/roles/BE-4.md)
3. **Nguồn chuẩn thiết kế & hợp đồng chính thức (`APPROVED`):**
   - [contracts/README.md](contracts/README.md) & [contracts/APPROVAL.md](contracts/APPROVAL.md) — Unified F1 Integration Contract **package 1.0.1**.
   - [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/schemas/f1.schema.json](contracts/schemas/f1.schema.json), [contracts/service-contract.json](contracts/service-contract.json), [contracts/data-contract.json](contracts/data-contract.json).
   - [docs/database/schema_F1.md](docs/database/schema_F1.md) — Logical schema **F1 v1.1** (`schema_version: "1.1"`).
4. **Bản đồ code & tài liệu thực thi liên quan đến task:**
   - [docs/architecture/F1_File_Organization_Proposal.md](docs/architecture/F1_File_Organization_Proposal.md) — Bản đồ runtime sau các PR refactor #25–#29 (kết hợp cập nhật PR #21).
   - [frontend/DESIGN.md](frontend/DESIGN.md) (nếu làm việc trên Frontend).
   - Các ghi chú thực thi trong `docs/implementation/`: [F1_EXECUTION.md](docs/implementation/F1_EXECUTION.md), [WP0_CONTRACT_ADDENDUM.md](docs/implementation/WP0_CONTRACT_ADDENDUM.md), [WP2_DATABASE.md](docs/implementation/WP2_DATABASE.md), [WP2A_NOTES.md](docs/implementation/WP2A_NOTES.md), [WP2B_NOTES.md](docs/implementation/WP2B_NOTES.md), [WP2C_NOTES.md](docs/implementation/WP2C_NOTES.md), [WP3_API.md](docs/implementation/WP3_API.md), [WP4_WORKFLOW.md](docs/implementation/WP4_WORKFLOW.md), [WP4_NOTES.md](docs/implementation/WP4_NOTES.md), [DEMO_ENVIRONMENT.md](docs/implementation/DEMO_ENVIRONMENT.md).

---

## 3. Thứ tự ưu tiên chỉ dẫn (Instruction Priority)

Khi thực thi nhiệm vụ, agent tuân theo thứ tự ưu tiên từ cao xuống thấp:

1. **System / Developer / User instructions** trực tiếp trong phiên làm việc và quyết định mới nhất được Project Owner xác nhận rõ ràng.
2. **Root [`AGENTS.md`](AGENTS.md)** (tài liệu này).
3. **Nested `AGENTS.md`** gần thư mục/file đang sửa hơn (nếu được bổ sung về sau).
4. **Role Guide** (`docs/team-coordination/roles/<ROLE>.md`) và **Task Spec** cụ thể của nhiệm vụ đang làm.
5. **Official Contracts (`contracts/` package 1.0.1) & Logical Schema (`docs/database/schema_F1.md` v1.1)**.
6. **Code runtime hiện tại + bộ kiểm thử (`backend/`, `frontend/`, `supabase/`, `tests/`)**.
7. **Tài liệu lịch sử / ghi chú quá trình (`README.md` gốc, `BAN_GIAO.md`, `docs/handoff/*`)**.

> **Quy tắc khi phát hiện xung đột:** Không âm thầm chọn một phía, không tự vượt quyền sửa contract hoặc ghi đè file của role khác. Hãy dừng phần xung đột, ghi nhận bằng [templates/CONFLICT_REPORT_TEMPLATE.md](docs/team-coordination/templates/CONFLICT_REPORT_TEMPLATE.md) hoặc cập nhật [OPEN_DECISIONS.md](docs/team-coordination/OPEN_DECISIONS.md) và gắn trạng thái `BLOCKED` / `NEEDS_DECISION`.

---

## 4. An toàn Git & Repository (Repo Safety)

- **Tuyệt đối không làm việc trực tiếp trên `main`:** Không checkout để sửa `main`, không commit lên `main`, không push lên `main`, không tự merge vào `main`.
- **Làm việc trên branch riêng cho từng task/role:** Đặt tên theo quy ước `feat/fe1-<slug>`, `feat/fe2-<slug>`, `feat/be1-<slug>`, `feat/be2-<slug>`, `feat/be3-<slug>`, `feat/be4-<slug>`, `fix/<role>-<slug>`, hoặc `docs/<slug>`.
- **Base branch rõ ràng:** Tạo branch từ `origin/main` mới nhất sau `git fetch origin` (hoặc nhánh tích hợp được Project Owner chỉ định rõ). Không tự nhánh từ một feature branch cũ chưa kiểm chứng.
- **Cách ly phiên làm việc:** Khi chạy nhiều session Codex/Claude trên cùng máy hoặc khi working tree chính đang có thay đổi chưa commit, bắt buộc dùng `git worktree` riêng cho từng session.
- **Cấm lệnh phá hủy:** Không chạy `git reset --hard`, `git clean -fd`, `git push --force`, rebase phá hủy lịch sử chung, hoặc stash/discard thay đổi chưa commit của người dùng.

---

## 5. An toàn Bí mật & Thông tin nhạy cảm (Secret Safety)

- **Tuyệt đối không đưa secret vào repo:** Không commit API key (`DEEPSEEK_API_KEY`), Supabase service-role/secret key, DB password (`SUPABASE_DB_PASSWORD`), `RPC_SIGNING_SECRET_BASE64`, JWT thật, hoặc file `.env` / `.env.local` / `.env.*` chứa giá trị thật.
- **Không in hoặc trích xuất secret:** Không `cat`/`echo`/log giá trị biến môi trường nhạy cảm ra terminal, PR description, worklog, test fixture hoặc tài liệu. Chỉ báo cáo trạng thái `PRESENT` hoặc `MISSING`.
- **Ranh giới khóa AI & DB:** `DEEPSEEK_API_KEY`, `RPC_SIGNING_SECRET_BASE64` và thông tin quản trị DB **chỉ tồn tại ở backend/server-side**. Frontend tuyệt đối không nhận hoặc gọi trực tiếp DeepSeek API.
- **Kiểm tra trước khi commit:** Bắt buộc chạy `git status`, `git diff --staged` và `git diff --check` để đảm bảo không lọt credential, file tạm hoặc lỗi khoảng trắng.

---

## 6. An toàn Hợp đồng & Schema (Contract Safety)

- **Nguồn chuẩn hiện hành:** Unified F1 Integration Contract **package 1.0.1 — APPROVED** (`contracts/`) và Logical Schema **F1 v1.1** (`docs/database/schema_F1.md`).
- **Cấm tự ý sửa contract đã duyệt:** Không một agent nào được tự ý thêm/bớt/sửa field trong `contracts/openapi.yaml`, `contracts/schemas/f1.schema.json`, `contracts/service-contract.json`, `contracts/data-contract.json`, hoặc `docs/database/schema_F1.md` chỉ để khớp với code của mình.
- **Phân biệt yêu cầu mới và contract hiện hành:** Các yêu cầu F1 mới của người dùng (ví dụ: priority `0.1 | 0.5 | 1`, `color`, bỏ Free Time trên UI thay bằng Personalized Working Time, upload image/calendar/document, từ chối audio...) được ghi nhận tại [PRODUCT_REQUIREMENTS_AND_DECISIONS.md](docs/team-coordination/PRODUCT_REQUIREMENTS_AND_DECISIONS.md) với trạng thái **chưa áp dụng vào contract 1.0.1 (`NOT YET APPLIED`)**. Khi task chạm tới thay đổi contract/schema, phải đi qua [CONTRACT_CHANGE_PROTOCOL.md](docs/team-coordination/CONTRACT_CHANGE_PROTOCOL.md).
- **Cấm tạo bản sao contract:** Không tạo OpenAPI thứ hai, JSON Schema thứ hai, hoặc bảng copy endpoint/schema độc lập gây lệch chuẩn.

---

## 7. Quyền sở hữu File & Module (Ownership)

- Mỗi agent chỉ được sửa các file/đường dẫn nằm trong `Allowed Paths` của role mình tại [FILE_OWNERSHIP.md](docs/team-coordination/FILE_OWNERSHIP.md) và trong Task Spec được giao.
- Không cho phép hai agent đồng thời sửa cùng một file dùng chung (`Shared File`) hoặc tạo các file migration (`supabase/migrations/*.sql`) xung đột thứ tự.
- Nếu cần thay đổi ở module thuộc role khác: không tự sửa lấn vùng; hãy tạo yêu cầu phụ thuộc (`Dependency / Handoff Request`) theo [INTEGRATION_PROTOCOL.md](docs/team-coordination/INTEGRATION_PROTOCOL.md) và đánh dấu phần chờ là `BLOCKED`.

---

## 8. Nguyên tắc Kỹ thuật (Engineering Rules)

- **Audit trước khi sửa:** Đọc code thực tế và test hiện hữu trước khi thay đổi; không dựa vào mô tả cũ trong `README.md` gốc hoặc tài liệu lịch sử.
- **Test-first & Bảo toàn kiểm thử:** Viết hoặc cập nhật test chứng minh hành vi; **tuyệt đối không xóa, skip hoặc làm yếu assertion** của các bộ test độc lập (`backend/tests/acceptance_sol/`, `backend/tests/acceptance_api_sol/`, `supabase/tests/`, `supabase/tests_concurrency/`) để làm xanh CI giả tạo.
- **Trung thực về bằng chứng (Evidence Integrity):** Không bịa đặt kết quả chạy test, SHA commit hay PR URL. Phân biệt rõ:
  - Test thuần / unit / mock transport (`PASS` local)
  - Test tích hợp với Supabase local thật (`pgTAP`, concurrency, HTTP integration)
  - Nghiệm thu live với DeepSeek API thật / cloud Supabase / trình duyệt thật.
  Mục nào chưa chạy hoặc thiếu môi trường phải ghi rõ `NOT_RUN` hoặc `BLOCKED`.
- **Bảo toàn tài liệu:** Giữ nguyên các comment/docstring giải thích có giá trị và cập nhật tài liệu điều phối/handoff khi thay đổi có ảnh hưởng liên nhóm.

---

## 9. Quy trình Thực thi Chuẩn (Standard Workflow)

Mọi task của agent phải đi qua 6 bước tuần tự:

```text
1. INSPECT  → Kiểm tra branch/worktree, đọc AGENTS.md + Role Guide + Task Spec + Contract + Code thực tế
2. PLAN     → Xác nhận phạm vi file được phép sửa, dependencies, contract impact và kế hoạch test
3. IMPLEMENT→ Thực hiện thay đổi tối thiểu, đúng kiến trúc và ranh giới ownership
4. TEST     → Chạy bộ kiểm thử tương ứng (Contract / Backend / DB / Frontend) và ghi nhận kết quả thực
5. REVIEW   → Kiểm tra git status, git diff, git diff --check, quét secret và kiểm tra vi phạm ownership
6. HANDOFF  → Commit trên branch riêng, điền PR/Handoff checklist với đầy đủ bằng chứng đã làm sạch
```

---

## 10. Tiêu chuẩn Hoàn thành (Definition of Done)

Một task **CHỈ** được phép báo `DONE` khi thỏa mãn đồng thời tất cả các điều kiện:

- [ ] Đạt toàn bộ Acceptance Criteria đã nêu trong Task Spec.
- [ ] Chỉ sửa các file trong phạm vi được phép của role/task; không vi phạm [FILE_OWNERSHIP.md](docs/team-coordination/FILE_OWNERSHIP.md).
- [ ] Không vi phạm hoặc tự ý sửa `contracts/` package 1.0.1 và `schema_F1.md` v1.1 khi chưa có phê duyệt theo [CONTRACT_CHANGE_PROTOCOL.md](docs/team-coordination/CONTRACT_CHANGE_PROTOCOL.md).
- [ ] Tất cả các bài test bắt buộc của phạm vi thay đổi đã chạy và có số liệu thực tế (`pass/fail/skip/not_run`); không làm yếu test cũ.
- [ ] `git diff --check` sạch, không có secret/credential/file `.env` hoặc artifact build (`dist/`, `node_modules/`, `__pycache__/`).
- [ ] Có báo cáo bàn giao theo [templates/WORK_HANDOFF_TEMPLATE.md](docs/team-coordination/templates/WORK_HANDOFF_TEMPLATE.md) và PR theo [templates/PR_TEMPLATE.md](docs/team-coordination/templates/PR_TEMPLATE.md) kèm danh sách reviewer đúng vai trò.
