# Hướng Dẫn Vai Trò `FE-1` — Task / Planner / Calendar / Confirmation

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`FE-1`** |
| **Nhóm (Team)** | Frontend (hỗ trợ Claude Code hoặc OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận giao diện và logic client thuộc miền Công việc (Task), Lịch tuần (Planner/Calendar) và Xem trước/Phê duyệt Đề xuất (Confirmation Preview) |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) và [`frontend/DESIGN.md`](../../../frontend/DESIGN.md) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`FE-1` chịu trách nhiệm toàn bộ trải nghiệm người dùng trên trang **Lập kế hoạch (`Planner`)** và các thành phần quản lý công việc / lịch tuần:

1. **Task Form & Task Detail:** Biểu mẫu tạo/xem chi tiết công việc; hiển thị tách biệt **tên công việc (`title`)** và **tên môn học (`course_label`)** (không gộp tên môn vào `title`); ánh xạ đúng các trường `duration` (`estimated_minutes`), `priority` (`0.1, 0.5, 1` theo quyết định `OD-001`), `color`, `description` và `start time` (theo quyết định `OD-002`).
2. **Planner / Calendar View & Timezone:** Lịch tuần (`WeekCalendar.tsx`), đồng bộ hiển thị ngày/giờ theo múi giờ sản phẩm `Asia/Ho_Chi_Minh` (`OD-005`).
3. **Sticky Date Header & Weekday Date:** Tiêu đề thứ/ngày cố định (`sticky`) khi cuộn dọc lịch và hiển thị ngày cụ thể (`dd/MM`) cạnh/dưới từng thứ trong tuần (`FE1-003`).
4. **Proposal / Confirmation Preview & Partial Feedback:** Hiển thị bản xem trước đề xuất lịch (`ProposalReview.tsx` + preview trên `WeekCalendar.tsx`), danh sách cảnh báo (`warnings`), thời lượng chưa xếp được (`unscheduled duration` / `unallocated_minutes` khi `coverage = PARTIAL`), và tích hợp nút **Duyệt (`APPROVE`) / Từ chối (`REJECT`)** gửi đúng `ActionReference` qua `POST /v1/decisions`.

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) (hoặc [`CLAUDE.md`](../../../CLAUDE.md)) & [`docs/team-coordination/README.md`](../README.md).
2. [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`frontend/DESIGN.md`](../../../frontend/DESIGN.md) — Kiến trúc state (`App.tsx` vs `Planner.tsx`), quy tắc CSS cascade trong `src/styles/`, bảng màu `--sf-*`, accessibility (vùng bấm tối thiểu 44px, bàn phím, `:focus-visible`) và GSAP (`useGSAP`).
4. [`contracts/README.md`](../../../contracts/README.md) (mục 2, 3), [`contracts/openapi.yaml`](../../../contracts/openapi.yaml) và [`contracts/schemas/f1.schema.json`](../../../contracts/schemas/f1.schema.json).
5. Code thực tế trong `frontend/src/`:
   - `frontend/src/pages/Planner.tsx`
   - `frontend/src/features/planner/{WeekCalendar.tsx,ProposalReview.tsx,TaskPanel.tsx,usePlanner.ts,proposal.ts,plannerAgent.ts}`
   - `frontend/src/api/{types.ts,endpoints.ts,mappers.ts,pending.ts,useServerData.ts}`
   - `frontend/src/types/{task.ts,planner.ts}`, `frontend/src/utils/date.ts`, `frontend/src/styles/planner.css`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa trực tiếp (`Allowed Changes — Primary Owner`)
- `frontend/src/pages/Planner.tsx`
- `frontend/src/features/planner/WeekCalendar.tsx`
- `frontend/src/features/planner/ProposalReview.tsx`
- `frontend/src/features/planner/TaskPanel.tsx`
- `frontend/src/features/planner/usePlanner.ts`
- `frontend/src/features/planner/proposal.ts` & `frontend/src/features/planner/proposal.test.ts`
- `frontend/src/features/planner/plannerAgent.ts` & `frontend/src/features/planner/plannerAgent.test.ts`
- `frontend/src/types/task.ts` & `frontend/src/types/planner.ts`
- `frontend/src/utils/date.ts`
- `frontend/src/styles/planner.css`
- Các thư mục mở rộng dành sẵn cho `FE-1` khi cần tách component con: `frontend/src/features/tasks/**`, `frontend/src/features/schedule/**`, `frontend/src/features/proposals/**`.

### 3.2. File dùng chung cần Co-Review (`Shared Files — Cần phối hợp FE-2 & BE-4`)
- `frontend/src/App.tsx`
- `frontend/src/api/{types.ts,endpoints.ts,mappers.ts,mappers.test.ts,pending.ts,useServerData.ts}`
- `frontend/src/components/ui/{Button,Card,Modal}.tsx`
- `frontend/src/styles/{index,tokens,base,layout,cards,overlays,overrides}.css`

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM** sửa bất kỳ file nào trong `backend/**`, `supabase/**`, `contracts/**` hoặc `docs/database/schema_F1.md`.
- **CẤM** sửa vùng của `FE-2`: `frontend/src/features/assistant/**`, `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/styles/{assistant,history,home,auth}.css`.
- **CẤM** sửa trang demo ngoài phạm vi F1: `frontend/src/pages/Study.tsx`, `frontend/src/styles/study.css`.
- **CẤM** tự bịa cấu trúc JSON request/response khác với `contracts/openapi.yaml` hoặc tự gán `approved=true` mà không gửi đúng `ActionReference` của server.
- **CẤM** đưa secret/API key vào frontend hoặc sửa `dist/`, `node_modules/`.

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận định nghĩa schema/types/fixtures cho Task và Timezone từ **`BE-1`** (`BE1-001`, `BE1-002`) và quyết định `OD-001`, `OD-002`, `OD-005` sau khi đóng băng tại `INT-001`.
  - Nhận cấu trúc `PlanProposal`, `coverage` (`PARTIAL`), `warnings` và `unallocated_minutes` từ **`BE-2`** (`BE2-001`, `BE2-002`).
  - Nhận hợp đồng điều phối `POST /v1/actions`, `POST /v1/decisions`, `POST /v1/actions/{id}/review` từ **`BE-4`** (`BE4-001`..`003`).
  - **Lưu ý:** Task **`FE1-003` (Sticky Date Header + ngày cụ thể cạnh thứ)** không phụ thuộc vào thay đổi contract backend và có thể triển khai ngay!
- **Đầu ra bàn giao (Downstream):**
  - Cung cấp UI/mapper đã đồng bộ cho bước tích hợp `INT-002` và kiểm thử trình duyệt `INT-003` cùng `FE-2` và `BE-4`.

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **FE1-001** | Task Form & Task Detail UI tách riêng `title` và `course_label`, hỗ trợ `duration`, `priority`, `color`, `description`, `start time` theo contract đã duyệt tại `INT-001`; nối `POST /v1/actions` (`create_task_candidate`) trong `endpoints.ts` / `mappers.ts` | `NEEDS_DECISION` (`OD-001`, `OD-002`, `OD-006`) |
| **FE1-002** | Đồng bộ hiển thị lịch tuần (`WeekCalendar.tsx`, `mappers.ts`, `date.ts`) theo múi giờ sản phẩm `Asia/Ho_Chi_Minh` | `IN_PROGRESS` (`OD-005`) |
| **FE1-003** | `Sticky Date Header` trên `WeekCalendar.tsx` / `planner.css` và hiển thị ngày cụ thể (`dd/MM`) cạnh/dưới từng thứ trong tuần | `NOT_STARTED` (Sẵn sàng làm ngay) |
| **FE1-004** | Hoàn thiện `ProposalReview.tsx` và calendar preview hiển thị rõ diff, `warnings`, `unscheduled duration` (`PARTIAL`), và nút Approve/Reject theo đúng `ActionReference` | `IN_PROGRESS` |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `FE-1` bắt buộc chạy từ thư mục gốc (hoặc thư mục `frontend/`) và ghi nhận kết quả thực tế:

```powershell
# 1. Chạy unit tests của Planner và API mappers/client
node --test frontend/src/features/planner/plannerAgent.test.ts frontend/src/features/planner/proposal.test.ts frontend/src/api/client.test.ts frontend/src/api/mappers.test.ts

# 2. Kiểm tra định dạng code bằng oxfmt
npm --prefix frontend run format

# 3. Kiểm tra kiểu TypeScript (strict)
npx --prefix frontend tsc --noEmit

# 4. Kiểm tra đóng gói production Vite
npm --prefix frontend run build

# 5. Kiểm tra diff sạch
git diff --check
```

---

## 7. Tiêu chuẩn Hoàn thành & Checklist Bàn giao (Done Criteria & Handoff Checklist)

- [ ] Chỉ sửa các file thuộc quyền sở hữu của `FE-1` (hoặc có co-review của `FE-2`/`BE-4` nếu chạm `frontend/src/api/*` hay `App.tsx`).
- [ ] Không phá vỡ Chế độ Demo khi không có biến `VITE_*` và hoạt động đúng với backend thật ở Chế độ API.
- [ ] Đảm bảo khả năng tiếp cận (accessibility) theo `frontend/DESIGN.md` mục 6: điều hướng bàn phím, `:focus-visible`, không chỉ dùng màu sắc để báo trạng thái, tôn trọng breakpoints `1250px / 800px / 480px`.
- [ ] Toàn bộ test (`node --test`), `tsc --noEmit` và `npm run build` đều PASS.
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md).
