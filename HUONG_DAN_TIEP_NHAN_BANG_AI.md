# Hướng dẫn tiếp nhận StudyFlow AI bằng AI — từng bước

Điểm bàn giao: **05/11/2026**. Tài liệu hướng dẫn nhận bộ ZIP và tiếp tục công việc; không tuyên bố MVP đã hoàn thành.

## 1. Hiểu đúng bộ ZIP

`workspace/` là snapshot toàn bộ source tại lúc bàn giao, không có `.git`, dependencies hay credentials. Snapshot có cả **WP0 chưa commit**.

Branch GitHub có lịch sử và phần đã commit nhưng chưa chứa toàn bộ WIP. Vì vậy cách tiếp nhận là **clone branch để có Git/history, sau đó chép snapshot để khôi phục phần đang dở**.

Các file trong kit:

- `BAN_GIAO.md`: đọc đầu tiên.
- `workspace/`: source hiện tại, gồm WIP.
- `git/StudyFlow-F1.bundle`: lịch sử Git tới điểm bàn giao, có thể dùng khi không clone được qua mạng.
- `git/working-tree.patch`: diff phần tracked chưa commit, phục vụ review/khôi phục thay thế.
- `evidence/`: log test tại lúc đóng gói.
- `manifest.json`: SHA256 source, HEAD và trạng thái kiểm tra.
- `README_KIT.md`: cách khôi phục bằng bundle.

## 2. Chuẩn bị

Người nhận cần quyền truy cập repo `chp0703/StudyFlow-AI`, Git, Python 3.12+ và IDE/AI họ sử dụng. Docker và Supabase CLI cần khi kiểm tra DB local.

Giải nén `StudyFlow_F1_handoff_v1_2026-11-05.zip`. Ví dụ thư mục kit thực tế là:

```text
C:\Work\StudyFlow_F1_handoff_v1_2026-11-05
```

Trong thư mục đó phải thấy `BAN_GIAO.md`, `workspace/`, `git/`, `evidence/`. Nếu công cụ giải nén tạo thêm một cấp thư mục, dùng đường dẫn bên trong tương ứng ở các bước tiếp theo.

## 3. Clone đúng branch

Mở PowerShell. Ví dụ dưới đây dùng thư mục mới `C:\Work\StudyFlow-AI`; nếu đã có repo ở đó, chọn nơi khác để tránh ghi đè công việc có sẵn.

```powershell
New-Item -ItemType Directory -Force -Path C:\Work
Set-Location C:\Work

git clone --branch feat/f1-mvp-intergration https://github.com/chp0703/StudyFlow-AI.git StudyFlow-AI
Set-Location C:\Work\StudyFlow-AI

git branch --show-current
git rev-parse HEAD
```

Điểm bàn giao đã được xác minh:

```text
Branch: feat/f1-mvp-intergration
HEAD:   52ee7c86b8fa3d957e52ea7856a2afed38531275
```

Giữ nguyên chính tả `intergration` trong tên branch.

**Nếu HEAD khác:** nhờ AI so sánh branch hiện tại với điểm bàn giao trước khi chép snapshot. Nhóm có thể đã cập nhật code; không tự `reset --hard` hoặc chép đè phiên bản mới.

Nếu không thể clone GitHub, xem cách clone bundle trong `README_KIT.md`. Bundle không mang theo tài khoản GitHub của người cũ; kiểm tra remote trước khi push.

## 4. Khôi phục WIP chưa commit

Nếu HEAD khớp và working tree vừa clone sạch, chạy:

```powershell
$kitRoot = 'C:\Work\StudyFlow_F1_handoff_v1_2026-11-05'
$repoRoot = 'C:\Work\StudyFlow-AI'

Get-ChildItem -LiteralPath "$kitRoot\workspace" -Force |
    Copy-Item -Destination $repoRoot -Recurse -Force

Set-Location $repoRoot
git status --short
```

Nhiều file modified/untracked lúc này là **đúng trạng thái bàn giao**. Không cần apply `working-tree.patch` thêm sau khi đã chép snapshot. Không dùng `git clean`/`reset --hard` để làm sạch WIP.

Từ đây chỉ mở và làm việc trong **`C:\Work\StudyFlow-AI`**, tránh mở nhầm thư mục `workspace/` của bộ ZIP.

## 5. Mở repo bằng AI chính và gửi prompt này

Sao chép nguyên khối sau vào chat AI chính:

```text
Bạn tiếp quản StudyFlow AI F1 MVP.

Repo đã clone branch feat/f1-mvp-intergration và overlay snapshot bàn giao,
bao gồm WIP chưa commit. Hãy đọc:
1. BAN_GIAO.md
2. docs/handoff/CONTEXT.md
3. docs/handoff/KE_HOACH_TIEP_THEO.md
4. docs/handoff/RUNBOOK.md
5. docs/handoff/PROMPTS.md

Kiểm tra Git và source thực tế trước khi sửa. Không bắt đầu phân tích lại
bốn branch từ đầu, không reset/clean làm mất WIP.

Bạn là AI chính: quản lý kế hoạch/Git, viết test độc lập, chạy kiểm chứng
và review. Giao từng gói implementation cho AI coding thứ hai; chỉ một
implementer sửa workspace mỗi lúc.

Trạng thái bàn giao:
- WP1 scheduler đã nghiệm thu, commit5d29d2d.
- WP0 contract1.0.1 đang WIP: checker fail và16test còn2fail.
- DB/API/orchestrator/live chưa hoàn thành.
- User đã duyệt A/B/C/D và cho phép push branch tích hợp; chưa cho merge main.

Việc đầu tiên: thiết lập môi trường, tái hiện lỗi WP0, review nguyên nhân,
giao implementer sửa; tự chạy lại checker/tests rồi mới nghiệm thu.
Không sửa hoặc giảm assertion để làm xanh. Không coi mock/SQL parse
là bằng chứng DB/security/live đã đạt.

Hãy báo ngắn trạng thái xác minh và hành động tiếp theo, rồi triển khai.
```

AI chính nên là model suy luận mạnh mà người nhận có quyền dùng. Yêu cầu ban đầu chọn Sol 6.1 High; nếu dùng model khác, ghi rõ model thực tế.

## 6. Để AI chính dựng môi trường và tái hiện baseline

Làm theo `docs/handoff/RUNBOOK.md`. Ví dụ dùng Python thật đã cài trên máy mới:

```powershell
Set-Location C:\Work\StudyFlow-AI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-acceptance.txt
.\.venv\Scripts\python.exe -m pip install -r supabase\tests_concurrency\requirements.txt
```

Không commit `.venv`; thêm ignore local hoặc dùng venv ngoài repo. Nếu `py` không có, chọn Python executable thật trên máy. Không sao chép đường dẫn Python/PYTHONPATH riêng của người cũ.

Kiểm tra đầu tiên:

```powershell
$py = '.\.venv\Scripts\python.exe'

& $py -B contracts/check_contract.py
& $py -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_contract_addendum.py -v
& $py -B -m unittest discover -s backend/tests/acceptance_sol -v
& $py -B -m unittest discover -s backend/tests/unit -t . -v
& $py -B -m unittest discover -s tests -v
& $py -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_http_contract.py -v
```

Baseline đã ghi trong kit:

| Phần | Trạng thái lúc đóng gói |
|---|---|
| Scheduler acceptance | 33 test pass |
| Planner unit | 24 test pass |
| TV2 regression | 78 test pass |
| Contract 1.0.1 | 16 test, 2 failures; checker cũng fail |
| HTTP API | 30 methods có sẵn, nhưng setup lỗi missing factory; **0 test thực thi**, không phải đã pass |
| Concurrency DB | Đã viết 6 scenario, chưa chạy DB |

WP0 fail ở continuation chứa kết quả READ `{items:[],next_cursor:null}`. Generic `ToolResult` dùng union `oneOf` bị trùng shape giữa hai loại danh sách. Reviewer phải tái hiện và kiểm source trước khi giao sửa; không đổi empty list thành nonempty để né lỗi.

Chưa cần credentials cloud để sửa WP0. Log trong kit là bằng chứng tại lúc đóng gói, không tự cập nhật sau khi người nhận sửa source.

## 7. Nối AI coding thứ hai

Yêu cầu ban đầu là Gemini 4 Argon High qua **official Antigravity CLI `agy`**. Máy cũ đã gọi thật thành công bằng Google sign-in, không API key và không computer use. Máy mới dùng tài khoản/quota riêng.

Sau khi cài official CLI và đăng nhập, kiểm tra:

```powershell
agy --version
agy models
agy -p 'Reply READY without using tools.' --model gemini-4-argon-high --effort high --output-format json
```

Tên model/quyền dùng phải kiểm trên tài khoản mới; không mặc định mọi gói đều có cùng quyền. Nếu không có AGY/Argon, dùng AI coding khác được người dùng cho phép và ghi rõ model thực tế.

AI chính dùng prompt mẫu trong `docs/handoff/PROMPTS.md`. Với gói WP0, chỉ cho sửa `contracts/`, không sửa acceptance tests, runtime, SQL hoặc Git. Có mẫu permissions ở `docs/handoff/session-permissions.example.json`; cần kiểm scope/đường dẫn trước khi dùng. Không bật bỏ qua toàn bộ permissions.

## 8. Vận hành vòng implement → test → review

1. AI chính chốt baseline SHA, working-tree status, contract và test trước.
2. Giao AI coding một gói nhỏ, phạm vi file rõ ràng; chỉ một implementer sửa code mỗi lúc.
3. Khi implementer trả kết quả, AI chính tự đọc diff và chạy test. Không nghiệm thu chỉ từ lời báo cáo.
4. Fail thì gửi case tái hiện, expected/actual và log để sửa tiếp. Không giảm assertions cho xanh.
5. Pass thì review quyền/transaction/invariants liên quan, chạy dependency thật khi gate yêu cầu, rồi commit tiếng Anh và push branch tích hợp.
6. Context đầy thì mở phiên mới có handoff. Chỉ fallback Flash High khi có bằng chứng Argon hết quota thật; không giả báo model hoặc test đã chạy.

AI chính giữ Git/test/quyết định nghiệm thu. AI coding giữ phần implementation được giao. Không để hai AI sửa runtime đồng thời trên workspace chung.

## 9. Thứ tự tiếp tục kế hoạch

**Chốt WP0 → WP2a → WP2b → WP2c → WP3 → WP4 → G3.**

| Gói | Nội dung chính |
|---|---|
| WP0 | Sửa/test/review contract 1.0.1 đang dở; giữ logical schema1.1, 8 endpoint/10 operation. |
| WP2a | DB boundary, role/grants/RLS, infrastructure, canonical JSON/HMAC verifier; migration009+, giữ lịch sử001–008. |
| WP2b | Task/settings/windows, pending/presentation, receipts, các helper và continuation recovery. |
| WP2c | Proposal/snapshot, approve/reject, stale, atomic commit, concurrency/rollback thực. |
| WP3 | FastAPI/JWT/JWKS, RPC adapter/signing, đủ API/read views. |
| WP4 | Hội thoại/state machine, scripted extractor rồi DeepSeek, multi-intent/approval/restart. |
| G3 | Môi trường thật, migrations đã kiểm chứng, live journeys, NLU benchmark và bàn giao UI. |

Chi tiết tiêu chí chuyển bước nằm trong `docs/handoff/KE_HOACH_TIEP_THEO.md` và các file `docs/implementation/WP*.md`.

## 10. Giữ nguyên các quyết định và đầu vào quan trọng

- Backend sản phẩm vẫn dùng **DeepSeek API**; Google Pro/Argon chỉ là công cụ phát triển.
- User đã duyệt toàn bộ A/B/C/D cho contract1.0.1 và cho phép push branch tích hợp. Chưa được merge main.
- Supabase project ref: `phomrutsdhdgejlskwcb`. Mới xác minh public JWKS ES256; chưa kiểm đủ quyền/schema/history/dữ liệu. Không reset cloud.
- Credentials cấu hình ngoài Git theo `.env.example` và `DEMO_ENVIRONMENT.md`; không gửi secret/token vào chat hoặc lấy credential của người cũ.
- Test mock/SQL parse không thay bằng chứng DB/security/live. Mục nào chưa chạy phải ghi NOT_RUN.

Người nhận chỉ cần bộ ZIP, quyền repo/tài khoản của họ và tài liệu này để tiếp tục; không cần mang cả lịch sử chat vào AI mới.
