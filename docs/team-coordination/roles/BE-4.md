# Hướng Dẫn Vai Trò `BE-4` — Chat / Task Draft / API Integration Coordinator

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`BE-4`** |
| **Nhóm (Team)** | Backend (OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận Điều phối Hội thoại (`Chat Orchestration`), Chỉnh sửa Bản nháp Công việc (`Task Draft Editing`), Quản lý vòng đời `PendingAction` (`Recovery / Cancel / Resume / Idempotency`), Điều phối API liên miền (`FastAPI / HTTP / RPC Client`) và Điều phối Tích hợp Contract FE↔BE |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md) và [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`BE-4` là chủ sở hữu của **tầng Điều phối Nghiệp vụ (`Orchestrator`) & Cổng Giao tiếp HTTP (`FastAPI`)**, đồng thời là **Điều phối viên Tích hợp Contract (`API Integration Coordinator`)**:

1. **Chat Orchestration & Task Draft Editing Owner:** Chủ trì `backend/app/orchestrator/chat.py` và `actions.py`, quản lý hàng đợi đa ý định bền vững (`workflow_continuations`), làm rõ thông tin thiếu (`NEEDS_CLARIFICATION`), cập nhật/chỉnh sửa `TaskCandidate` nháp (`BE4-001`), và chuyển candidate đã được người dùng review từ `BE-3`/`FE-2` vào luồng xác nhận chuẩn.
2. **Pending Action Lifecycle, Recovery, Cancel, Resume & Idempotency Owner:** Chủ trì `backend/app/orchestrator/receipts.py`, `actions.py`, `chat.py` — đảm bảo claim/replay/release/complete `api_request_receipts` (lease 120s), một `PendingAction` đang chờ trên mỗi hội thoại, khôi phục và bắt buộc xem lại (`requires_review` + `POST /v1/actions/{id}/review`), hủy nháp (`cancel_pending_action`) và tiếp tục hàng đợi sau khi quyết định (`resume`).
3. **Cross-Domain API Orchestration Owner:** Chủ trì `backend/app/main.py`, `core/{config,security,contract}.py`, `clients/rpc.py` (ký HMAC-SHA256 canonical JSON), và `api/v1/{routes,http,workflow,chat}.py`.
4. **Contract Index & FE/BE Integration Coordinator:** Duy trì chỉ mục contract và ma trận tương thích giữa `BE-1`, `BE-2`, `BE-3` với `FE-1`, `FE-2` theo [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md).
   > **Ranh giới thẩm quyền:** `BE-4` điều phối tính nhất quán của contract nhưng **không tự ý ghi đè quyết định chuyên môn của Domain Owner** (`BE-1` về DB/schema, `BE-2` về Scheduler/Approval, `BE-3` về NLU/File Parser) và không thay quyền phê duyệt phạm vi sản phẩm của **Project Owner**.

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) & [`docs/team-coordination/README.md`](../README.md).
2. Toàn bộ các tài liệu trong `docs/team-coordination/`: [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`ARCHITECTURE_AND_RUNTIME_RULES.md`](../ARCHITECTURE_AND_RUNTIME_RULES.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`INTEGRATION_PROTOCOL.md`](../INTEGRATION_PROTOCOL.md), [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`contracts/README.md`](../../../contracts/README.md), [`contracts/APPROVAL.md`](../../../contracts/APPROVAL.md), [`contracts/openapi.yaml`](../../../contracts/openapi.yaml), [`contracts/schemas/f1.schema.json`](../../../contracts/schemas/f1.schema.json), [`contracts/service-contract.json`](../../../contracts/service-contract.json), [`contracts/data-contract.json`](../../../contracts/data-contract.json), [`contracts/acceptance-cases.md`](../../../contracts/acceptance-cases.md).
4. [`docs/architecture/F1_File_Organization_Proposal.md`](../../architecture/F1_File_Organization_Proposal.md), [`docs/implementation/WP3_API.md`](../../implementation/WP3_API.md), [`docs/implementation/WP4_WORKFLOW.md`](../../implementation/WP4_WORKFLOW.md), [`docs/implementation/WP4_NOTES.md`](../../implementation/WP4_NOTES.md).
5. Code thực tế:
   - `backend/app/main.py`, `backend/app/core/{config,security,contract}.py`, `backend/app/clients/rpc.py`
   - `backend/app/api/v1/{routes,http,workflow,chat}.py`
   - `backend/app/orchestrator/{actions,chat,receipts,workflow_ports,workflow_shared}.py`
   - `backend/tests/unit/{test_action_rejection,test_receipt_recovery,test_workflow_errors}.py`
   - `backend/tests/integration/{test_http_local_supabase,test_chat_local_supabase}.py`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa trực tiếp (`Allowed Changes — Primary Owner`)
- `backend/app/main.py` (bắt buộc bảo toàn chữ ký `create_app(settings=None, *, rpc_transport=None, llm_transport=None, jwks_transport=None, clock=None, extractor=None)`)
- `backend/app/core/{config,security,contract}.py`
- `backend/app/clients/rpc.py`
- `backend/app/api/v1/{routes,http,workflow,chat}.py`
- `backend/app/orchestrator/{actions,chat,receipts,workflow_ports,workflow_shared,README}.py`
- `backend/tests/unit/{test_action_rejection,test_receipt_recovery,test_workflow_errors}.py`
- `backend/tests/integration/{test_http_local_supabase,test_chat_local_supabase}.py`
- Tài liệu điều phối trong `docs/team-coordination/**` (khi cập nhật tiến độ `TASK_BOARD.md` và `OPEN_DECISIONS.md`).

### 3.2. File dùng chung cần Co-Review (`Shared Files`)
- `contracts/**` (chỉ sửa khi thực hiện Bước 11–12 của [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md) sau khi có phê duyệt của Project Owner và đồng thuận của Domain Owner).
- `backend/requirements.txt`, `backend/requirements-acceptance.txt`, `.github/workflows/*.yml`.

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM** tự ý sửa thuật toán trong `backend/app/f1/scheduler/**` hoặc `backend/app/f1/planning/generate.py` (thuộc `BE-2`).
- **CẤM** tự ý sửa prompt/extractor trong `backend/app/nlu/**` (thuộc `BE-3`).
- **CẤM** tự ý tạo hoặc sửa các file SQL migration trong `supabase/migrations/**` (thuộc `BE-1` và `BE-2`).
- **CẤM** sửa code giao diện trong `frontend/**` (thuộc `FE-1` và `FE-2`).
- **CẤM** làm yếu hoặc sửa bộ test nghiệm thu độc lập trong `backend/tests/acceptance_api_sol/**`, `backend/tests/acceptance_sol/**`, `supabase/tests/06_sol_rpc_boundary.sql`, `07_sol_internal_addendum.sql`.
- **CẤM** để `orchestrator/` import ngược `api/v1/` hoặc `fastapi` (phải đi qua `workflow_ports.py` / `workflow_shared.py`).

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận các RPC và quy tắc xác thực dữ liệu Task / Timezone / Working Time từ **`BE-1`**.
  - Nhận `generate()` và các RPC `get_scheduling_context`, `persist_plan_proposal`, `approve_study_plan`, `reject_study_plan` từ **`BE-2`**.
  - Nhận `Extractor` và kết quả trích xuất tệp trung gian từ **`BE-3`**.
- **Đầu ra bàn giao (Downstream):**
  - Cung cấp 8 HTTP endpoints chuẩn (hoặc thêm endpoint mới sau `INT-001`) kèm thông báo lỗi theo catalog cho **`FE-1`** và **`FE-2`**.

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **BE4-001** | Hợp đồng & logic điều phối cho phép chỉnh sửa `TaskCandidate` nháp (`Task Draft Editing`) và nhận candidate đã được người dùng xác nhận từ bước Extraction Review (`BE-3`/`FE-2`) | `NEEDS_DECISION` (`OD-001`, `OD-004`, `OD-006`) |
| **BE4-002** | Hoàn thiện và kiểm chứng toàn bộ các trường hợp khôi phục, hủy, xem lại và tiếp tục `PendingAction` / `workflow_continuations` (`ORCH-01`..`ORCH-06`, `DB-11`, `DB-15`) | `IN_PROGRESS` |
| **BE4-003** | Duy trì sổ đăng ký tích hợp API, đảm bảo `contracts/check_contract.py` và ma trận tương thích FE↔BE luôn đồng bộ | `IN_PROGRESS` |
| **BE4-004** | Điều phối và viết kiểm thử tích hợp E2E liên miền (`backend/tests/integration/`) kết nối đầy đủ các luồng của `BE-1`, `BE-2`, `BE-3` | `BLOCKED` (chờ `INT-001` & các task domain) |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `BE-4` bắt buộc chạy và ghi nhận kết quả thực tế:

```powershell
# 1. Kiểm tra tính toàn vẹn của Contract Package
python -B contracts/check_contract.py
python -B backend/scripts/generate_contract_schema_migration.py --check
python -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_contract_addendum.py -v

# 2. Chạy unit tests của Orchestrator và legacy regression tests
python -B -m unittest discover -s backend/tests/unit -t . -v
python -B -m unittest discover -s tests -v

# 3. Chạy bộ kiểm thử HTTP Contract Acceptance (30+ cases với MockTransport)
python -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_http_contract.py -v

# 4. Khi có Supabase PostgreSQL local, chạy bộ kiểm thử tích hợp HTTP & Chat thật
python -B -m unittest discover -s backend/tests/integration -t . -v

# 5. Kiểm tra diff sạch
git diff --check
```

---

## 7. Tiêu chuẩn Hoàn thành & Checklist Bàn giao (Done Criteria & Handoff Checklist)

- [ ] Bảo toàn tuyệt đối nguyên tắc: mọi thao tác ghi đều qua `claim_api_receipt` → `record_source_message` → chuẩn bị `ActionPresentation` / `ActionReference` → nhận `UserDecision` khớp đúng `action_id`/`action_version`/`target_type`/`target_id`/`target_version` → thực thi RPC có chữ ký HMAC → `complete_api_receipt`.
- [ ] Không bao giờ suy diễn sự đồng ý từ văn bản chat tự do hoặc từ đầu ra của LLM; không lộ SQL/stack trace/secret trong `Error.details`.
- [ ] Giữ nguyên chữ ký `create_app(...)` và các đường dẫn re-export tương thích (`backend/app/api/v1/chat.py`).
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md) và cập nhật [`TASK_BOARD.md`](../TASK_BOARD.md).
