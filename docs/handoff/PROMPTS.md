# Prompt và cách điều phối hai AI

## Thiết lập

AI chính/reviewer nên dùng model suy luận mạnh mà người nhận có quyền sử dụng (yêu cầu ban đầu là Sol6.1High). AI implement là ArgonHigh qua official `agy`, hoặc công cụ coding được người dùng mới cho phép. Nếu không có model cụ thể thì nói rõ, không tự nhận đã gọi nó.

AI chính giữ Git/test/tiêu chí nghiệm thu. Implementer nhận từng gói và chỉ sửa source đúng scope. Không cho cả hai sửa runtime cùng lúc. Các bộ acceptance của reviewer không giao quyền chỉnh cho implementer. Research/read-only review có thể song song.

## Prompt mở chat AI chính — dán nguyên khối

```text
Bạn tiếp quản StudyFlow AI F1 MVP từ bộ handoff này, không bắt đầu lại.
Đọc BAN_GIAO.md và docs/handoff/CONTEXT.md, KE_HOACH_TIEP_THEO.md,
RUNBOOK.md, sau đó kiểm tra Git/working tree thực tế. Nếu dùng ZIP, workspace/
có WIP chưa commit; clone branch GitHub đơn thuần không có WP0 mới nhất.

Vai trò của bạn là reviewer/điều phối: tự lập tiêu chí và viết test độc lập,
chạy kiểm chứng, quản lý Git và quyết định nghiệm thu. Giao implementation cho
Gemini4ArgonHigh qua official agy; chỉ một implementer sửa workspace mỗi lúc.
User đã duyệt toàn bộ A/B/C/D cho contract1.0.1 và cho push branch tích hợp.
Không hỏi lại hai quyền đó. Chưa được merge main. Commit tiếng Anh.

Trạng thái: WP1 accepted commit5d29d2d, 33+24+78 tests pass và schedulerCI xanh.
WP0 machine-readable1.0.1 đang WIP: checker fail và16 acceptance còn2fail;
DB vẫn8 migrations, API factory chưa có. Không báo MVP đã hoàn tất.
Việc đầu tiên là tái hiện/fix WP0 continuation READ empty-list union, review
toàn diff/fixtures/semantics, test pass rồi mới WP2a/b/c, WP3, WP4, G3.

Không giảm assertion để làm xanh; nếu test sai contract, bạn phải giải thích
và sửa có bằng chứng. Không dùng mock làm bằng chứng transaction/security/live.
Giữ backendDeepSeek, custompolicy, noTTLdraft/proposal và approval authority.
Không reset cloud; không đọc/in token Google hoặc gửi secrets vào chat.
Tiếp tục làm phần được phép; hỏi thiếu đầu vào cụ thể và giải thích vì sao.
```

## Prompt giao implementer — dùng cho từng gói

```text
Implement [WP và mục tiêu cụ thể] trong [workspace], branch
feat/f1-mvp-intergration, baseline [SHA reviewer vừa kiểm tra].
Preserve existing WIP. Đọc [handoff/source contract liên quan] trước.
Allowed edit paths: [danh sách ngắn]. Không sửa [tests reviewer/contracts
ngoài phạm vi/migration history/Git/frontend/secrets].

Contract/behavior: [interface, invariant và input/output đã duyệt].
Reviewer đã chạy trước: [command, sốtest, expected/actual chính xác].
Tiêu chí đạt: [danh sách có thể kiểm chứng]. Dependencies: [phần đã/chưa có].

Hãy implement, không dừng ở kế hoạch. Dùng native file-edit tools; không chạy
shell/Git/test nếu reviewer chưa giao phần đó. Reviewer chạy kiểm tra riêng.
Không tạo thành công giả hoặc đổi assertions/fixtures độc lập để làm xanh.
Trả paths, quyết định, giới hạn và kiểm tra thực sự đã chạy; không bịa pass.
Chưa bắt đầu gói tiếp theo.
```

## Prompt tiếp tục ngay WP0 cho Argon

```text
Tiếp quản WP0 từ snapshot. User đã duyệt A/B/C/D package1.0.1/logical1.1.
Chỉ sửa contracts/. Đọc WP0_CONTRACT_ADDENDUM.md và các tests độc lập.
Reviewer hiện thấy checker fail official checkpoint-advance-arguments.json;
16 independent tests còn2fail:
test_continuation_cursor_and_completed_prefix_are_consistent và
test_wait_and_advance_are_distinct_closed_unions.
Valid READ search result {items:[],next_cursor:null} bị genericToolResult
READ.data.oneOf loại vì trùng SearchTasksData/TimeWindowListData.
Sửa union/operation binding theo semantics đúng, giữ operation-specific
validation và closed fields. Không sửa tests, không biến empty list thành
nonempty để né lỗi, không nới tùy ý mọi JSON. Review thêm toàn bộ WP0;
lời báo cáo cũ có vài tên schema không khớp source nên lấy code/contract
làm chuẩn. Không chạy shell/Git/tests; báo paths và giới hạn để reviewer kiểm.
```

## Vòng sửa và review

1. Lưu SHA + working-tree status, criteria, test baseline trước khi giao.
2. Chờ implementer dừng; đọc diff và tự chạy test. Không chỉ đọc báo cáo.
3. Fail: gửi repro nhỏ, expected/actual/log, phạm vi cần sửa; không số vòng cố định.
4. Lỗi lặp: reviewer phân tích gốc và thu scope. Context đầy thì phiên mới có handoff.
5. Pass: reviewer đọc quyền/transaction/edge cases liên quan, kiểm dependency thật khi gate yêu cầu; commit tiếng Anh và push integration.

Một reviewer khác có thể nhận prompt: “Chỉ read-only review diff [SHA→workingtree]
với contract [files]. Chỉ báo blocker có valid-input repro, source line và tác động;
không sửa runtime/Git, không coi mock là bằng chứng DB.” Đừng review lan man vô hạn.

## AGY CLI

Trên máy cũ đã chạy được; máy mới cần official CLI + Google sign-in riêng.

```powershell
Set-Location E:\TDTT\StudyFlow-AI
agy --version
agy models
agy -p 'Reply READY without using tools.' --model gemini-4-argon-high --effort high --output-format json
```

Sau ping thành công, dùng `-p` với prompt hoặc đọc prompt từ file qua PowerShell:

```powershell
$taskPrompt = Get-Content -LiteralPath .\task_prompt.txt -Raw
agy -p $taskPrompt --model gemini-4-argon-high --effort high --settings .\session-permissions.json --output-format json --print-timeout 30m
```

Đọc docs chính thức để tạo scoped permissions theo đường dẫn máy mới. Dùng
`session-permissions.example.json` trong thư mục này làm mẫu cho WP0; chạy từ
repo root và đổi scope khi sang gói khác. Dùng
`permissions.allow` cho implementation paths, `deny` cho command(*), tests,
.git, secrets và phần ngoài scope; default/Ask cho phần còn lại. Đừng bật
`--dangerously-skip-permissions`. Đừng auto-approve toàn workspace rồi tưởng
allowlist là hàng rào tuyệt đối. Reviewer vẫn phải kiểm diff.

Theo dõi cả JSON status, stderr và actual diff: exit0 có thể kèm tool soft-denied.
Pin model cụ thể, không Auto routing. Chỉ khi Argon báo hết quota thật mới chuyển
`--model gemini-3.8-flash-high --effort high`. Không đưa credential/cache của máy
cũ cho người mới. Hết đăng nhập thì người dùng tự làm official sign-in.

Tài liệu: https://antigravity.google/docs/cli/headless/ và
https://antigravity.google/docs/permissions/ . CLI app conversation cũ không chắc
resume được bằng CLI ID; có handoff file thì phiên mới vẫn tiếp tục được.
