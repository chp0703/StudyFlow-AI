# DESIGN.md — StudyFlow AI

Hướng dẫn cho thành viên nhóm. Đọc trước khi sửa UI.

## 1. Dự án là gì

Ứng dụng React cho không gian học tập của sinh viên. Product scope gồm Planner, Assessment & Adaptive Revision và Daily AI Learning; giao diện hiện tại mới hoàn thiện nền tảng Planner và một phần khung Daily Learning.

| Trang | Nội dung |
|---|---|
| **Trang chủ** (`Assistant`) | Chat với trợ lý AI + 3 thẻ tóm tắt: Công việc hôm nay, Deadline 5 ngày tới, Thời gian học |
| **Lập kế hoạch** (`Planner`) | Khung chat điều khiển lịch tuần (agent theo luật: thêm / dời / xóa) |
| **Học tập** (`Study`) | Khung tài liệu, ghi chú và đồng hồ; sẽ phát triển thành Daily AI Learning |

Assessment & Adaptive Revision chưa có màn hình riêng và không được coi là đã triển khai chỉ vì scope sản phẩm đã được phê duyệt.

Ứng dụng chạy ở **hai chế độ**:

- **Chế độ demo** (không đặt biến `VITE_*`): dữ liệu học tập (công việc, tệp) chỉ nằm trong bộ nhớ và bắt đầu rỗng; không có backend, đăng nhập, đồng bộ tài khoản, đọc tệp, truy xuất nguồn hay AI thật. Mọi quy tắc demo bên dưới áp dụng nguyên vẹn.
- **Chế độ API** (đặt đủ `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`): đăng nhập email + mật khẩu qua Supabase, công việc, giờ làm việc/bận và kế hoạch đọc/ghi qua Planner API; trợ lý và khung chat của Planner gọi `POST /v1/messages`. Việc ghi chỉ xảy ra khi người dùng bấm xác nhận một thao tác do server phát hành. Assessment và Daily Learning chưa có API. Tệp đính kèm chưa được hỗ trợ (nút bị khóa).

Riêng **lịch sử hội thoại** được lưu trong IndexedDB của trình duyệt (đã được duyệt cho riêng tính năng này); ở chế độ API, supabase-js lưu phiên đăng nhập trong localStorage và Planner giữ `conversation_id` cùng tham chiếu thao tác đang chờ (không lưu nội dung) trong localStorage.

Quy tắc bắt buộc:
- Giữ các dòng tuyên bố demo/nguồn. Không trình bày dữ liệu minh họa như bằng chứng học tập đã xác minh.
- Không tuyên bố đã thành thạo, đã tải lên, đã trích xuất tài liệu hay có AI thật.
- Không thêm analytics, dịch vụ ngoài hoặc lưu trữ nào khác ngoài IndexedDB cho lịch sử hội thoại, phiên Supabase và các khóa `studyflow_*` nêu trên nếu chưa được duyệt.
- Ngày, môn học, đáp án và tin nhắn mẫu phải rõ là minh họa.

## 2. Công nghệ và lệnh

React 19 · Vite 8 · TypeScript (strict) · Tailwind CSS v4 (`@tailwindcss/vite`) · icon `lucide-react` · animation `gsap` + `@gsap/react` · formatter oxfmt. Node 22, npm. Chuỗi giao diện bằng tiếng Việt.

| Lệnh | Mục đích |
|---|---|
| `npm install` | cài đặt |
| `npm run dev` | chạy dev (`$PORT`, mặc định 5173) |
| `npm run build` | build production vào `dist/` |
| `npm run preview` | chạy bản build |
| `npm run format` | format bằng oxfmt |
| `npx tsc --noEmit` | kiểm tra kiểu (không có script lint) |
| `node --test <file>` | chạy test (không có `npm test`) |

Test hiện có (`node --test <file>`): `src/features/assistant/{conversationHistory,apiAssistant}.test.ts`, `src/features/planner/{plannerAgent,proposal}.test.ts`, `src/api/{client,mappers}.test.ts`.

Trước khi mở PR: `npm run format && npm run build && npx tsc --noEmit`.

## 3. Cấu trúc thư mục

```text
index.html                document shell, favicon, meta noindex
public/brand/             logo + favicon (phục vụ tại /brand/...), lưu bằng Git LFS
src/main.tsx              mount <App/>, import styles/index.css
src/App.tsx               khung ứng dụng: điều hướng, state dùng chung (tasks), modal, toast
src/pages/                Planner, Study
src/components/           HomeSummary (3 thẻ tóm tắt); ui/ Button, Card, Modal
src/features/assistant/   Assistant (UI), assistantService (trả lời mẫu), conversationHistory (IndexedDB)
src/features/planner/    plannerAgent (lệnh chat -> chỉnh lịch, chỉ chế độ demo), proposal, TaskPanel
src/features/auth/       LoginPage (chế độ API)
src/api/                 client (fetch + token + Idempotency-Key + lỗi catalog), endpoints, types (DTO hợp đồng),
                         mappers (DTO -> Task/sự kiện lịch/ô rảnh bận/đề xuất), auth (supabase-js), useServerData, pending
src/types/                kiểu dùng chung (Task, hợp đồng assistant)
src/utils/                hàm ngày (date.ts)
src/styles/               xem mục 5
vite.config.ts            chỉ có plugin react + tailwind
```

Sinh tự động: `dist/`, `node_modules/` — không sửa, không commit.

## 4. Kiến trúc

- **Không có router.** `App.tsx` giữ `page` (`Assistant | Planner | Study`), `tasks` dùng chung và toast `notice`. Khi đổi trang, focus chuyển về tiêu đề trang.
- **Vị trí state quan trọng.** `Assistant` và `Study` luôn được mount, chỉ thêm `hidden` khi không active để giữ bản nháp chat, tệp và đồng hồ. `Planner` bị unmount nên state riêng (phản hồi chat, tuần đang xem) bị reset khi đổi trang. `tasks` nằm ở `App` nên được giữ.
- **Trang chủ** = `Assistant` + `components/HomeSummary` trong `.home-layout`. Ba thẻ ẩn khi cuộc trò chuyện có tin nhắn. Chọn một cuộc trò chuyện trong Lịch sử thì panel lịch sử tự đóng.
- **Assistant** có state tách biệt: `Assistant.tsx` (UI) → `assistantService.ts` (`getAssistantReply`, stub dùng regex, không phải API client) → hợp đồng ở `src/types/assistant.ts`. Mỗi cuộc trò chuyện có UUID, bản nháp và bản nháp làm rõ riêng. Đề xuất được khôi phục phải được xem lại trước khi xác nhận demo. Nội dung hội thoại không bao giờ cho phép ghi vào backend.
- **Lịch sử hội thoại**: `conversationHistory.ts` lưu mỗi cuộc trò chuyện một bản ghi IndexedDB và một khóa riêng cho cuộc đang mở. Nếu lưu trữ lỗi, UI vẫn chạy trong bộ nhớ và báo không giữ được sau khi tải lại. Không đổi tên các giá trị đã lưu như `demo_acknowledged`, `valid_demo_draft` nếu chưa có migration.
- **Planner**: `runPlannerCommand(input, tasks)` trả về `{ tasks, reply }`; hiểu "thêm / dời / xóa", giờ từ 8 đến 17. `Task.date` và `Task.hour` đặt công việc lên lịch. Đây là bản theo luật, sẽ thay bằng agent thật sau.
- **Phạm vi Planner hiện tại**: theo `docs/features/planner/schema.md` v1.1, luồng chính là công việc → working time/busy time → tự lập lịch → duyệt. Lệnh `thêm … lúc …`, `dời`, `xóa` (thêm/dời khối thủ công) nằm ngoài contract Planner hiện tại; chúng chỉ còn trong bản mẫu để thử giao diện. Scope sản phẩm đầy đủ còn gồm Assessment và Daily Learning theo `docs/product/requirements.md`.
- **Đề xuất → Duyệt → Lưu (Planner)**: lệnh chat không sửa lịch trực tiếp. `Planner` tạo một `Proposal` (`src/types/planner.ts`, `features/planner/proposal.ts`) giữ trạng thái kế tiếp và danh sách thay đổi; lịch hiển thị bản xem trước (viền nét đứt + chữ "Đề xuất", "Sẽ xóa") cùng thanh Duyệt/Từ chối. Chỉ khi Duyệt mới `setTasks` và tăng `revision`; nếu `revision` đã đổi thì đề xuất chuyển `STALE` và khóa nút Duyệt. `tasks`, `proposal`, `revision` nằm ở `App` nên giữ khi đổi trang. Lệnh mới xếp chồng lên đề xuất đang chờ. Thông báo duyệt lưu lịch hiển thị ngay trong thẻ Lịch và tự động ẩn sau 3.5s (giống thông báo xóa/thêm tài liệu).
- **Khung giờ rảnh/bận (Planner)**: lệnh `rảnh|bận <ngày> từ Nh đến Mh` (và `xóa rảnh|bận <ngày>`) cũng đi qua luồng Đề xuất → Duyệt. Các khung này không được suy ra từ phần giờ hiển thị; bấm giờ trên lịch để điền sẵn lệnh thêm việc (hỗ trợ ngày `dd/mm`). Giờ bận bị bỏ qua khi xếp; xếp ngoài giờ rảnh chỉ cảnh báo trong phản hồi (quy tắc đề xuất, chưa chốt trong SRS).
- **Bảng công việc (Planner)**: cột phải cạnh lịch (`features/planner/TaskPanel.tsx`), có tìm kiếm + lọc trạng thái. Trạng thái suy ra, không lưu: **Nháp** = thuộc đề xuất đang chờ, **Đã xác nhận** = đã xếp lên lịch và được duyệt, **Chưa xếp** = chưa có ngày/giờ. Mỗi trạng thái có icon + chữ. Lệnh `tạo công việc <tên> hạn <ngày> [N giờ]` tạo việc chưa xếp.
- **Lập kế hoạch tự động (Planner)**: lệnh `lập kế hoạch` xếp các việc chưa xếp theo hạn nộp rồi mức ưu tiên, mỗi việc một khối 60 phút vào giờ trống sớm nhất (bỏ giờ bận; nếu ngày có khai giờ rảnh thì chỉ dùng giờ rảnh). Cùng đầu vào cho cùng kết quả. Việc không vừa trước hạn nằm trong mục "Chưa xếp được (n)" của thanh đề xuất (mã `INSUFFICIENT_AVAILABILITY`); phần xếp được vẫn xem trước và duyệt riêng. Quy tắc khối 60 phút là đề xuất, chưa chốt trong SRS.
- **Chú thích, huy hiệu (Planner)**: đề xuất không tự hết hạn (Planner schema v1.1 đã bỏ `EXPIRED`), chỉ chuyển `STALE` khi lịch nền đổi. Hàng chú thích trên lịch có Đã xác nhận / Rảnh / Bận / Đề xuất; tuần không có việc thì hiện gợi ý lệnh mẫu. Bảng công việc có nút lọc "Tuần đang xem". Menu "Lập kế hoạch" hiện huy hiệu "Chờ duyệt" khi còn đề xuất chưa quyết định (đề xuất nằm ở `App` nên không mất khi đổi trang).
- **Chế độ API**: `App` đọc `tasks`, sự kiện lịch (mỗi lịch học một sự kiện), ô rảnh/bận và `revision` (= `schedule_revision`) từ `useServerData` và gọi `reload()` sau mọi thao tác có thể làm đổi dữ liệu. Chat của Planner gửi `POST /v1/messages`; trả lời `AWAITING_APPROVAL` thành `Proposal` (có `server.reference` = `ActionReference` giữ nguyên, không sửa) với thanh Duyệt/Từ chối gọi `POST /v1/decisions`; `NEEDS_CLARIFICATION` hiện câu hỏi, câu trả lời kế tiếp là tin nhắn mới. Mỗi lần gửi dùng một `Idempotency-Key`; gửi lại đúng nội dung sau lỗi tạm thời dùng lại khóa cũ. Sau khi tải lại trang, đề xuất đang chờ được dựng lại bằng `POST /v1/actions/{id}/review` từ tham chiếu đã lưu. Task panel hiện công việc từ server (Nháp/Đã xác nhận/Chưa xếp); lịch hiện các buổi học của kế hoạch hiện tại. Giờ hiển thị theo `Asia/Ho_Chi_Minh`; mỗi ngày có dải giờ hiển thị riêng, không ảnh hưởng lịch hoặc bộ xếp lịch.
- Dùng lại `Button`, `Card`, `Modal` (Modal là `<dialog>` gốc, có khôi phục focus) trước khi viết wrapper mới.
- Chọn tệp chỉ lưu tên và nhãn trạng thái; không tải lên hay đọc nội dung.
- Icon: chỉ dùng `lucide-react`.
- **Animation**: dùng GSAP qua hook `useGSAP` (`@gsap/react`), không tự viết `useEffect` + `gsap` để tránh rò rỉ khi unmount. Hiện có một hiệu ứng: ở `App.tsx`, mỗi lần `page` đổi, các `.card` và khung chat trang chủ đang hiển thị trượt từ dưới lên (48px, 0.5s, lệch nhau 0.08s, `clearProps` để không để lại style). Vì `Assistant` và `Study` chỉ bị `hidden` chứ không unmount, hiệu ứng gắn vào việc đổi trang chứ không gắn vào lúc mount. Khi thêm hiệu ứng mới, chỉ animate `transform` và `opacity`.

## 5. Giao diện và CSS

### Các file trong `src/styles/`

`index.css` chỉ chứa các `@import`. **Thứ tự import là thứ tự cascade** — rule sau ghi đè rule trước, nên không đổi thứ tự khi chưa kiểm tra.

| File | Nội dung |
|---|---|
| `tokens.css` | token thương hiệu `--sf-*`, bảng màu, `--bg-card`; khối `@theme` của Tailwind (`--color-*`, `--radius-card`) |
| `base.css` | reset toàn cục (`@layer base`), nút (`.button`, `.primary`, `.secondary`…), ô nhập |
| `layout.css` | khung ứng dụng: thanh trên, thanh bên, `.main-content`, tiêu đề trang |
| `cards.css` | `.card`, `.card-heading`, thẻ tóm tắt (`.summary-*`) |
| `overlays.css` | modal và toast |
| `overrides.css` | breakpoint responsive, sau đó các tinh chỉnh dùng chung. Cố ý để tinh chỉnh đứng **sau** media query |
| `assistant.css` | chat trợ lý |
| `history.css` | panel lịch sử hội thoại |
| `home.css` | bố cục trang chủ (chat + 3 thẻ), khung chat bo tròn |
| `planner.css` | trang Lập kế hoạch: khung chat và lịch tuần vừa khít màn hình |
| `study.css` | trang Học tập |

Mỗi trang có file CSS riêng; style dùng chung cho nhiều trang đặt trong `layout.css`, `cards.css`, `base.css`.

### Quy tắc

- Dùng token `--sf-*` hoặc biến ngữ nghĩa (`--color-primary`, `--color-ink`, `--color-line`…) trước khi thêm màu thô.
- Đặt style phần tử toàn cục trong `@layer base` để tiện ích Tailwind ghi đè được. Giữ `@import` ở đầu file.
- Dùng đúng tên class hiện có (`.button`, `.primary`, `.secondary`, `.card`, `.card-heading`).
- Khi thêm class mới, kiểm tra nó thực sự được dùng; xóa CSS không còn tham chiếu thay vì để lại.
- Bảng màu: primary `#596CF0`, indigo `#5064E9`, purple `#8B5CF6`, pink `#FF6B81`, orange `#FF9F43`, yellow `#FFE066`, teal `#22B8A7`; chữ chính `#17203B`, chữ phụ `#667085`; nền `#F7F8FF`; viền `#E5E8F4`.
- Nền thẻ: `--bg-card` (`rgba(255,255,255,0.94)`) kèm làm mờ nhẹ; thẻ bo `var(--radius-card)` (16px). Gradient thương hiệu: `linear-gradient(115deg, #596cf0, #8b5cf6 58%, #d657c7)`.
- Chrome (`.topbar`, `.sidebar`) là khối bo tròn nổi lên trên nền; đổi kích thước chúng phải kiểm tra lại `.main-content`.
- Logo bản sáng (`/brand/logo-horizontal-light-transparent.png`) dùng trên thanh trên sáng.
- Trang chủ và Lập kế hoạch vừa khít chiều cao màn hình, không cuộn trang: khung chat co giãn, ba thẻ ẩn khi chat; lịch có vùng cuộn riêng và mỗi ngày có dải giờ hiển thị độc lập. Giữ tính chất này khi sửa.

## 6. Khả năng tiếp cận (bắt buộc)

- Ưu tiên HTML ngữ nghĩa; mọi thứ dùng được bằng bàn phím.
- Giữ `:focus-visible` nhìn thấy được, skip link, khôi phục focus cho modal + phím Escape, và `aria-label` / `aria-current` / `aria-pressed`.
- Không chỉ dựa vào màu để biểu thị trạng thái, deadline, hoàn thành hay lỗi (thêm icon/chữ).
- Vùng bấm tối thiểu 44px. Ngoại lệ hiện có: nút chuyển tuần trong lịch cao 32px; không thêm ngoại lệ mới nếu chưa cần.
- Tôn trọng `forced-colors`; giữ các breakpoint 1250 / 800 / 480px. CSS (transition/animation) tôn trọng `prefers-reduced-motion` trong `overrides.css`. **Ngoại lệ có chủ đích:** hiệu ứng trượt thẻ bằng GSAP luôn chạy, không kiểm tra `prefers-reduced-motion`, theo quyết định của nhóm. Hiệu ứng mới có chuyển động lớn nên cân nhắc tắt khi người dùng chọn giảm chuyển động.
- Khi đổi trang, chuyển focus về tiêu đề trang.

## 7. Quy trình thay đổi

1. Đọc component và CSS của nó trước; khi sửa class, giá trị state hoặc primitive dùng chung, grep mọi nơi gọi.
2. Thay đổi nhỏ nhất đủ làm xong việc — không thêm abstraction, route, dependency hay lưu trữ nếu chưa có nhu cầu cụ thể.
3. `npm run format`, `npm run build`, `npx tsc --noEmit`, rồi xem giao diện trên trình duyệt nếu đổi bố cục/tương tác.
4. Báo lỗi build trung thực. Không commit secret, `.env`, `dist/`.
5. Trước khi push, ghi một mục vào `worklogs/<github-username>.md` theo `worklogs/sample.md`.

- **Giờ hiển thị lịch (FE-03)**: `CalendarDisplaySettings` giữ đúng một cặp bắt đầu/kết thúc cho từng thứ trong bộ nhớ frontend. Đây chỉ là phần nhìn của lịch, không gọi API, không tạo đề xuất, không sửa `TimeWindow` hay đầu vào bộ xếp lịch.
