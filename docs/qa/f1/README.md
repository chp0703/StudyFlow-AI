# Bộ Kiểm thử & Đánh giá Tự động Feature 1 (Intelligent Academic Planner)

Thư mục này chứa **bộ script chạy QA tự động**, **file hướng dẫn 2 trang dễ hiểu** và đầy đủ **5 Deliverables Kiểm toán & Kiểm thử E2E** cho Feature 1 (Planner) của StudyFlow AI.

## Chạy QA Tự động nhanh trong 2 phút

```bash
# 1. Chạy Auto-QA Backend + AI DeepSeek thật + Scheduler + DB (32 kịch bản E01–E14)
#    (Dùng --mode live nếu đã bật ./scripts/dev-up.sh; hoặc --mode embedded nếu chưa bật Docker)
python -B docs/qa/f1/run_f1_auto_qa.py --mode live --env-file .env.local --trials 3

# 2. Chạy Auto-QA Giao diện Frontend (bắt lỗi popup clarification.ts, 8.000 ký tự, retry 503 & unit tests)
node docs/qa/f1/run_f1_ui_qa.mjs

# (Tùy chọn) Chạy thêm trình duyệt Playwright test F5 Slow 3G & 8.005 ký tự thật trên Chrome:
node docs/qa/f1/run_f1_ui_qa.mjs --browser --url http://127.0.0.1:5173 --email <qa-email> --password <qa-pass>
```

> Báo cáo kết quả (`PASS / BUG` + độ trễ P50/P95) được lưu tự động tại `logs/f1-qa-reports/` (đã nằm trong `.gitignore`).

## Danh mục Tài liệu & Script trong `docs/qa/f1/`

1. **[F1_Huong_Dan_QA.pdf](F1_Huong_Dan_QA.pdf)** — *Hướng dẫn Cầm tay Chỉ việc cho QA (3 trang A4)*: Trang 1 chạy 2 lệnh tự động, Trang 2 thao tác cụ thể từng bước cho 3 việc QA thật làm trên Chrome, Trang 3 cách chụp bằng chứng báo Bug & 5 Cổng chặn Release.
2. **[F1_Tong_Hop_Loi_QA_Cho_DEV.md](F1_Tong_Hop_Loi_QA_Cho_DEV.md)** & **[F1_Bang_Nghiem_Thu_Fix.csv](F1_Bang_Nghiem_Thu_Fix.csv)** — *Đặc tả tổng hợp toàn bộ 9 báo cáo QA Feature 1 cho Team DEV*: Gộp chống trùng lặp 21 lỗi sản phẩm (`F1-FIX-01` → `F1-FIX-21`) + 1 phụ lục script QA (`F1-FIX-22`), dẫn chứng tận file/hàm/dòng code trên `main @ e366422`, kèm checklist GitHub và bảng CSV import thẳng Google Sheets để tick nghiệm thu.
3. **[run_f1_auto_qa.py](run_f1_auto_qa.py)** — *Script Auto-QA API & Real DeepSeek E2E*: Hỗ trợ `--mode live` (FastAPI + Local Supabase) và `--mode embedded`, đo `Pass@k` / `Pass^k`, tự khóa an toàn không chạm Cloud Supabase `phomrutsdhdgejlskwcb`.
4. **[run_f1_ui_qa.mjs](run_f1_ui_qa.mjs)** — *Script Auto-QA Frontend & Playwright Chaos*: Chạy kiểm chứng `clarification.ts`, giới hạn `8.000` ký tự, chính sách retry `503`, unit tests thuần TS và tùy chọn `--browser` phá giao diện.
5. **[01-repository-and-architecture-audit.md](01-repository-and-architecture-audit.md)** — *Deliverable 1: Repository & Architecture Audit* (luồng thực thi 11 bước, Active Model, ma trận Tools/Skills, 12 lỗi `CF-01..CF-12`).
6. **[02-requirements-and-metrics.md](02-requirements-and-metrics.md)** — *Deliverable 2: FR/NFR & Evaluation Metrics* (1–3 metric dễ hiểu cho từng requirement + 5 Release Gates).
7. **[03-e2e-test-plan.md](03-e2e-test-plan.md)** — *Deliverable 3: E2E Test Plan* (phương pháp Anthropic Agent Eval, 14 suites `E01–E14`, phân loại lỗi `RC-*`).
8. **[04-e2e-test-cases.md](04-e2e-test-cases.md)** — *Deliverable 4: 45 E2E Test Cases* (kèm [f1_e2e_test_cases.json](f1_e2e_test_cases.json) và [f1_e2e_test_cases.csv](f1_e2e_test_cases.csv) mở trên Excel/Google Sheets).
9. **[05-regression-checklist.md](05-regression-checklist.md)** — *Deliverable 5: 18-item Regression Checklist* trước mỗi bản build/release.
