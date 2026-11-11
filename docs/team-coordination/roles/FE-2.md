# Hướng Dẫn Vai Trò `FE-2` — Personalized Working Time / Upload Review / Assistant

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`FE-2`** |
| **Nhóm (Team)** | Frontend (hỗ trợ Claude Code hoặc OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận giao diện và logic client thuộc miền Khung giờ làm việc cá nhân hóa (Personalized Working Time), Tải tệp & Xem lại kết quả trích xuất (Upload & Extraction Review), và Trợ lý AI (Assistant) |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) và [`frontend/DESIGN.md`](../../../frontend/DESIGN.md) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`FE-2` chịu trách nhiệm toàn bộ trải nghiệm người dùng trên trang **Trang chủ / Trợ lý (`Assistant`)**, màn hình xác thực (`LoginPage`), thiết lập **Personalized Working Time** và luồng **Upload / Extraction Review**:

1. **Personalized Working Time UI & Gỡ bỏ "Free Time":** Xây dựng giao diện thiết lập thời gian làm việc cá nhân hóa và xóa các điểm vào (entry points) mang tên "Free Time / Giờ rảnh" trên giao diện người dùng theo yêu cầu được duyệt (`REQ-F1-07`, `REQ-F1-08`, `OD-003`).
2. **Upload UI (`image`, `calendar file`, `document`) & Chặn `audio` ở Client:** Cho phép người dùng chọn/kéo-thả đúng 3 nhóm định dạng tệp được duyệt (`image`, `calendar`, `document`); từ chối ngay tại client mọi tệp âm thanh (`audio/*`, voice note) đồng thời xử lý đúng phản hồi kiểm tra từ server (`BE-3`).
3. **Extraction Review & Correction UI:** Hiển thị các thông tin candidate trích xuất từ tệp (kèm các trường thiếu hoặc độ tin cậy thấp) để người dùng kiểm tra, chỉnh sửa và xác nhận trước khi chuyển vào luồng Task Draft / Proposal.
4. **Assistant & Task Draft Integration:** Duy trì giao diện hội thoại `Assistant.tsx`, lưu trữ lịch sử trong IndexedDB (`studyflow-assistant-history`), khôi phục trạng thái `requires_review` và hiển thị quá trình làm rõ/xác nhận `TaskCandidate` / `PendingAction`.

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) (hoặc [`CLAUDE.md`](../../../CLAUDE.md)) & [`docs/team-coordination/README.md`](../README.md).
2. [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`frontend/DESIGN.md`](../../../frontend/DESIGN.md) — Quy tắc lưu trữ IndexedDB (`studyflow-assistant-history`), hai chế độ Demo/API, quy tắc CSS cascade và khả năng tiếp cận.
4. [`contracts/README.md`](../../../contracts/README.md) (mục 2, 3, 4), [`contracts/openapi.yaml`](../../../contracts/openapi.yaml) và [`contracts/schemas/f1.schema.json`](../../../contracts/schemas/f1.schema.json).
5. Code thực tế trong `frontend/src/`:
   - `frontend/src/features/assistant/{Assistant.tsx,ChatComposer.tsx,ChatTranscript.tsx,ConversationSidebar.tsx,useConversationHistory.ts,conversationHistory.ts,apiAssistant.ts,assistantService.ts}`
   - `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/components/HomeSummary.tsx`
   - `frontend/src/api/{auth.ts,client.ts,config.ts,endpoints.ts,mappers.ts,types.ts,useServerData.ts}`
   - `frontend/src/types/assistant.ts`, `frontend/src/styles/{assistant,history,home,auth}.css`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa trực tiếp (`Allowed Changes — Primary Owner`)
- `frontend/src/features/assistant/Assistant.tsx`
- `frontend/src/features/assistant/ChatComposer.tsx`
- `frontend/src/features/assistant/ChatTranscript.tsx`
- `frontend/src/features/assistant/ConversationSidebar.tsx`
- `frontend/src/features/assistant/useConversationHistory.ts`
- `frontend/src/features/assistant/conversationHistory.ts` & `frontend/src/features/assistant/conversationHistory.test.ts`
- `frontend/src/features/assistant/apiAssistant.ts` & `frontend/src/features/assistant/apiAssistant.test.ts`
- `frontend/src/features/assistant/assistantService.ts`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/components/HomeSummary.tsx`
- `frontend/src/types/assistant.ts`
- `frontend/src/styles/{assistant,history,home,auth}.css`
- Các thư mục mở rộng dành sẵn cho `FE-2`: `frontend/src/features/availability/**` (cho Personalized Working Time UI), `frontend/src/features/chat/**` (cho Extraction Review/Correction UI).

### 3.2. File dùng chung cần Co-Review (`Shared Files — Cần phối hợp FE-1 & BE-4`)
- `frontend/src/App.tsx` (do `FE-1` điều phối chính; bắt buộc co-review khi thêm modal/panel thiết lập Working Time hoặc callback đồng bộ).
- `frontend/src/api/{auth.ts,client.ts,config.ts,endpoints.ts,mappers.ts,types.ts,useServerData.ts}`.
- `frontend/src/components/ui/{Button,Card,Modal}.tsx`.

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM** gọi trực tiếp DeepSeek API hoặc giữ bất kỳ `DEEPSEEK_API_KEY`, Supabase service-role key, `RPC_SIGNING_SECRET_BASE64` nào ở trình duyệt.
- **CẤM** sửa bất kỳ file nào trong `backend/**`, `supabase/**`, `contracts/**` hoặc `docs/database/schema_F1.md`.
- **CẤM** sửa vùng của `FE-1`: `frontend/src/pages/Planner.tsx`, `frontend/src/features/planner/**`, `frontend/src/styles/planner.css`.
- **CẤM** sửa trang `frontend/src/pages/Study.tsx` hoặc `frontend/src/styles/study.css`.
- **CẤM** thay đổi tên database IndexedDB (`studyflow-assistant-history`), object stores (`conversations`, `meta`) hoặc quy tắc bật cờ `requires_review` khi khôi phục đề xuất từ lịch sử nếu chưa có migration dữ liệu client được duyệt.

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận hợp đồng dữ liệu và quy tắc xác thực cho `Personalized Working Time` từ **`BE-1`** (`BE1-003`, `OD-003`).
  - Nhận ma trận định dạng tệp (`image`/`calendar`/`document`), quy tắc từ chối `audio` và cấu trúc `ExtractionCandidate` từ **`BE-3`** (`BE3-002`, `BE3-003`, `BE3-004`, `OD-004`).
  - Nhận hợp đồng chỉnh sửa Task Draft và khôi phục `PendingAction` từ **`BE-4`** (`BE4-001`, `BE4-002`, `OD-006`).
- **Đầu ra bàn giao (Downstream):**
  - Chuyển dữ liệu Task Draft / Working Time đã được người dùng xác nhận sang luồng lập lịch và hiển thị trên lịch tuần của **`FE-1`** (qua `onServerChange` / `reload()`).

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **FE2-001** | Giao diện `Personalized Working Time` và loại bỏ toàn bộ điểm vào "Free Time" trên UI người dùng theo quyết định tại `OD-003` / `INT-001` | `NEEDS_DECISION` (`OD-003`) |
| **FE2-002** | Giao diện Upload trong Assistant (`ChatComposer.tsx` / component con) chỉ nhận `image`, `calendar file`, `document`; chặn hoàn toàn `audio` / voice note ở client và hiển thị lỗi rõ ràng từ server | `NEEDS_DECISION` (`OD-004`) |
| **FE2-003** | Giao diện `Extraction Review & Correction` cho phép người dùng xem, sửa các trường thiếu/mơ hồ từ tệp và bấm xác nhận trước khi tạo Task Draft | `BLOCKED` (chờ `OD-004`, `BE3-003`) |
| **FE2-004** | Hoàn thiện tích hợp Assistant với luồng Task Draft, `NEEDS_CLARIFICATION`, `AWAITING_APPROVAL` và `POST /v1/actions/{id}/review` sau khi tải lại trang | `IN_PROGRESS` |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `FE-2` bắt buộc chạy từ thư mục gốc và ghi nhận kết quả thực tế:

```powershell
# 1. Chạy unit tests của Assistant, IndexedDB history và API client/mappers
node --test frontend/src/features/assistant/conversationHistory.test.ts frontend/src/features/assistant/apiAssistant.test.ts frontend/src/api/client.test.ts frontend/src/api/mappers.test.ts

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

- [ ] Chỉ sửa các file thuộc quyền sở hữu của `FE-2` (hoặc có co-review của `FE-1`/`BE-4` trên các file dùng chung).
- [ ] Không gọi trực tiếp bất kỳ dịch vụ AI nào từ trình duyệt; không lưu trữ thêm khóa localStorage/IndexedDB ngoài danh sách được phép trong `frontend/DESIGN.md`.
- [ ] Bảo toàn 100% các bài test trong `conversationHistory.test.ts` và `apiAssistant.test.ts`; bổ sung test mới cho validation chặn `audio` và luồng review tệp.
- [ ] Pass `npm run format`, `npx tsc --noEmit`, `npm run build` và `git diff --check`.
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md).
