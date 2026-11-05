# Bàn giao StudyFlow AI — F1 MVP

Cập nhật ngày **05/11/2026, giờ Việt Nam**. Đây là điểm bàn giao do người dùng sắp hết quota; không phải tuyên bố hoàn tất MVP.

## Đọc nhanh

- Repo: `chp0703/StudyFlow-AI`; workspace cũ `E:\TDTT\StudyFlow-AI`.
- Branch tiếp tục: **`feat/f1-mvp-intergration`** (giữ đúng chính tả này).
- HEAD lúc bắt đầu đóng gói: **`52ee7c86b8fa3d957e52ea7856a2afed38531275`**, đã push. `main` chưa merge.
- **WP1 scheduler/normalizer đã nghiệm thu**, commit `5d29d2d`.
- **WP0 contract 1.0.1 đang dở, CHƯA nghiệm thu**: Argon đã sửa file nhưng test độc lập còn 2 failures, checker cũng fail. Các sửa đổi này chưa commit; ZIP có snapshot đầy đủ và patch.
- **DB/API/orchestrator/live demo chưa hoàn thành.** DB vẫn chỉ có tám migration cũ; API chưa có `backend.app.main`.
- Không còn tác vụ implement mới được giao khi bàn giao. Lượt Argon WP0 đã trả kết quả; không cần điều khiển app Antigravity để tiếp tục.

## Những gì đã làm

| Hạng mục | Trạng thái và bằng chứng |
|---|---|
| Tích hợp 4 thành viên | Đã nhập TV1/TV2/TV3/TV4 vào branch tích hợp; SHA nguồn ở CONTEXT.md. |
| Scheduler + TimeWindow normalizer | 33 acceptance tests của Sol, 24 planner unit tests, 78 TV2 regression đã pass; 5 planner cases ×100 lần deterministic, không hard-constraint violation. CI scheduler cũng xanh. |
| Test độc lập | Đã có contract addendum 16 tests; HTTP 30 tests; SQL 03–07; 6 bài concurrency thực bằng psycopg; dataset NLU 40 câu Việt. Phần lớn chưa có runtime để đạt. |
| DB thật trong CI | Tám migration cũ replay thành công; baseline pgTAP 190 assertions, **128 fail**. Đó là bằng chứng phần thiếu, không phải DB đã đạt. |
| Contract bổ sung | Người dùng đã duyệt toàn bộ A/B/C/D cho package **1.0.1**, logical schema **1.1**; thêm 6 internal RPC + continuation infrastructure, giữ 8 endpoint/10 operation. |
| Công cụ Gemini | Official **Antigravity CLI `agy` 1.5.1** đã gọi thật `gemini-4-argon-high --effort high` thành công bằng Google sign-in, không API key, không computer use. |
| Môi trường demo | Có `.env.example`, hướng dẫn, script inventory chỉ đọc. Project ref `phomrutsdhdgejlskwcb`; chưa áp migration cloud. |

## Người tiếp nhận làm gì đầu tiên

1. Đọc [context](docs/handoff/CONTEXT.md), [kế hoạch tiếp tục](docs/handoff/KE_HOACH_TIEP_THEO.md), [prompt điều phối](docs/handoff/PROMPTS.md), [runbook](docs/handoff/RUNBOOK.md).
2. Nếu dùng ZIP: ưu tiên mở thư mục `workspace/` vì nó chứa **cả WIP chưa commit**. `git clone` branch từ GitHub một mình sẽ thiếu phần WP0 đang dở. Cách khôi phục lịch sử nằm trong `README_KIT.md` của ZIP.
3. Chạy lại checker và 16 test WP0; sửa lỗi continuation/result rỗng trước. Không sửa test để che lỗi.
4. Review diff WP0, kiểm tra tất cả fixtures và semantics; chỉ nghiệm thu/commit khi đạt. Sau đó làm WP2a → WP2b → WP2c → WP3 → WP4 → G3.

## Hai điểm dễ bỏ sót

- `contracts/VALIDATION.md` hoặc lời báo cáo của implementer không thay thế kết quả chạy của reviewer. Tại thời điểm bàn giao, checker **đang fail**. `evidence/` trong ZIP lưu log kiểm tra mới nhất; xem `RUNBOOK.md` để tái hiện.
- Google Pro/Argon là công cụ phát triển. **Sản phẩm vẫn dùng DeepSeek API**. Chưa có bằng chứng DeepSeek key/live test hoặc quyền/migration history/dữ liệu của project Supabase đã được kiểm tra.

ZIP không chứa `.env.local`, credential Google, `.git/config`, binaries `.tools`, dependencies hoặc cache máy cũ. Người mới dùng tài khoản/quota của họ và cài môi trường riêng.
