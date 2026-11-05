# DESIGN.md — StudyFlow AI

Hướng dẫn cho thành viên nhóm. Đọc trước khi sửa UI.

## 1. Dự án là gì

Prototype React để mô phỏng không gian học tập của sinh viên, gồm 3 trang:

| Trang | Nội dung |
|---|---|
| **Trang chủ** (`Assistant`) | Chat với trợ lý AI + 3 thẻ tóm tắt: Công việc hôm nay, Deadline 5 ngày tới, Thời gian học |
| **Lập kế hoạch** (`Planner`) | Khung chat điều khiển lịch tuần (agent theo luật: thêm / dời / xóa) |
| **Học tập** (`Study`) | Tài liệu, ghi chú và đồng hồ buổi học |

Dữ liệu học tập (công việc, tệp) chỉ nằm trong bộ nhớ và bắt đầu rỗng. Riêng **lịch sử hội thoại** được lưu trong IndexedDB của trình duyệt (đã được duyệt cho riêng tính năng này). Không có backend, đăng nhập, đồng bộ tài khoản, đọc tệp, truy xuất nguồn hay AI thật.

Quy tắc bắt buộc:
- Giữ các dòng tuyên bố demo/nguồn. Không trình bày dữ liệu minh họa như bằng chứng học tập đã xác minh.
- Không tuyên bố đã thành thạo, đã tải lên, đã trích xuất tài liệu hay có AI thật.
- Không thêm analytics, dịch vụ ngoài hoặc lưu trữ nào khác ngoài IndexedDB cho lịch sử hội thoại nếu chưa được duyệt.
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

Test hiện có: `src/features/assistant/conversationHistory.test.ts`, `src/features/planner/plannerAgent.test.ts`.

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
src/features/planner/     plannerAgent (lệnh chat -> chỉnh lịch)
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
- **Đề xuất → Duyệt → Lưu (Planner)**: lệnh chat không sửa lịch trực tiếp. `Planner` tạo một `Proposal` (`src/types/planner.ts`, `features/planner/proposal.ts`) giữ trạng thái kế tiếp và danh sách thay đổi; lịch hiển thị bản xem trước (viền nét đứt + chữ "Đề xuất", "Sẽ xóa") cùng thanh Duyệt/Từ chối. Chỉ khi Duyệt mới `setTasks` và tăng `revision`; nếu `revision` đã đổi thì từ chối với `STALE_PLAN_VERSION`. `tasks`, `proposal`, `revision` nằm ở `App` nên giữ khi đổi trang. Lệnh mới xếp chồng lên đề xuất đang chờ. Thông báo duyệt lưu lịch hiển thị ngay trong thẻ Lịch và tự động ẩn sau 3.5s (giống thông báo xóa/thêm tài liệu).
- **Khung giờ rảnh/bận (Planner)**: lệnh `rảnh|bận <ngày> từ Nh đến Mh` (và `xóa rảnh|bận <ngày>`) cũng đi qua luồng Đề xuất → Duyệt. Ô rảnh tô xanh, ô bận gạch chéo, đều kèm chữ "Rảnh"/"Bận"; bấm ô trống để điền sẵn lệnh thêm việc (hỗ trợ ngày `dd/mm`). Giờ bận bị bỏ qua khi xếp; xếp ngoài giờ rảnh chỉ cảnh báo trong phản hồi (quy tắc đề xuất, chưa chốt trong SRS).
- **Bảng công việc (Planner)**: cột phải cạnh lịch (`features/planner/TaskPanel.tsx`), có tìm kiếm + lọc trạng thái. Trạng thái suy ra, không lưu: **Nháp** = thuộc đề xuất đang chờ, **Đã xác nhận** = đã xếp lên lịch và được duyệt, **Chưa xếp** = chưa có ngày/giờ. Mỗi trạng thái có icon + chữ. Lệnh `tạo công việc <tên> hạn <ngày> [N giờ]` tạo việc chưa xếp.
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
- Trang chủ và Lập kế hoạch vừa khít chiều cao màn hình, không cuộn trang: khung chat co giãn, ba thẻ ẩn khi chat; hàng giờ của lịch co lại. Giữ tính chất này khi sửa.

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
