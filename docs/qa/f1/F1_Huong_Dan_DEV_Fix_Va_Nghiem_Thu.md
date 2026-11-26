# Hướng dẫn Sửa lỗi & Kiểm tra lại (Dành cho Team DEV)

Tài liệu này viết cho **DEV Backend, Frontend và AI/Prompt** biết cách: nhận lỗi từ QA mà không phải tự đi đọc từng file rời rạc, chạy tái hiện lại đúng lỗi trên máy mình trong 10 giây, sửa xong tự chạy lại cho chắc ăn rồi mới báo QA kiểm tra.

---

## 1. QA sẽ gom lỗi gửi cho DEV ở đâu? (DEV không phải đi lục nhiều file)

Team QA **không** gửi mỗi người 1 file rời rạc cho DEV tự mở ra đọc. Toàn bộ lỗi (dù là từ máy chạy tự động hay từ QA bấm tay trên Chrome) đều được QA **gom về 1 nơi chung** (trên **GitHub Issues** hoặc **1 bảng Sheet chung**) và gán đúng tên bạn DEV phụ trách:

- **Lỗi Backend / Lịch / Database** (nhãn `RC-BACKEND`, `RC-TOOL`, `RC-DB`) → Giao DEV Backend.
- **Lỗi Giao diện / Nút bấm / Ô nhập** (nhãn `RC-FE`) → Giao DEV Frontend.
- **Lỗi AI hiểu sai tiếng Việt / Prompt** (nhãn `RC-AGENT`) → Giao DEV AI / Prompt.

Khi bạn mở 1 Issue được giao cho mình, bên trong sẽ có **1 trong 2 dạng thông tin** sau:
- **Dạng 1 (Lỗi từ máy chạy tự động):** Ghi sẵn **Mã bài test** *(ví dụ: `F1-E01-02`)* và mô tả sai ở đâu.
- **Dạng 2 (Lỗi QA bấm tay trên Chrome):** Ghi sẵn **Câu QA đã gõ**, **2 ảnh chụp (khung Chat + trang Lịch)**, và **Mã tra log `X-Request-ID`**.

---

## 2. Làm sao chạy lại đúng cái lỗi đó trên máy mình?

Trước khi sửa code, bạn chạy tái hiện đúng cái lỗi trong Issue để nhìn tận mắt nó sai ở đâu:

### Trường hợp A: Issue có ghi Mã bài test (Ví dụ: `F1-E01-02`)
Mở terminal ngay tại thư mục gốc `StudyFlow-AI`, copy nguyên câu lệnh ví dụ dưới đây (chỉ cần đổi `F1-E01-02` thành mã lỗi trong Issue của bạn):

```bash
python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --env-file .env.local --case F1-E01-02 --trials 1
```

**Giải thích từng đoạn trong lệnh cho dễ hiểu:**
- `--mode embedded`: Tự chạy nhanh mà **không cần bật Docker/Supabase** *(nếu máy bạn đã bật web + Supabase local sẵn rồi thì đổi thành `--mode live`)*.
- `--env-file .env.local`: File chứa `DEEPSEEK_API_KEY` trên máy bạn *(nếu bạn lưu key ở file khác như `backend/.env` thì sửa lại đường dẫn tương ứng)*.
- `--case F1-E01-02`: Chỉ chạy **đúng 1 cái lỗi này** (mất ~10 giây), không phải chờ chạy hết cả bộ. Muốn chạy 2 lỗi cùng lúc thì viết liền dấu phẩy: `--case F1-E01-02,F1-E02-02`.
- `--trials 1`: Chạy thử **1 lần** để thấy lỗi hiện ra ngay.

Nếu Issue là **lỗi giao diện Frontend (`RC-FE`)**, bạn chỉ cần chạy đúng 1 dòng ngắn này:
```bash
node docs/qa/f1/run_f1_ui_qa.mjs
```

### Trường hợp B: Issue là lỗi QA bấm tay trên Chrome (không có mã `F1-...`)
1. Bật web local trên máy bạn, mở trình duyệt **đăng nhập tài khoản test**.
2. Gõ đúng câu tiếng Việt và bấm đúng các bước như trong 2 ảnh QA gửi để tự nhìn thấy lỗi.
3. Nếu lỗi làm backend văng mã `500` / `422`, lấy mã `X-Request-ID` trong Issue tìm (`Ctrl+F`) ở cửa sổ terminal đang chạy backend là thấy ngay dòng code bị lỗi.

---

## 3. Lúc sửa code nhớ giữ 4 nguyên tắc này

1. **Không tự lưu vào Database qua Chat:** Mọi tạo/sửa công việc, giờ rảnh/bận và lịch học chỉ được lưu chính thức khi đi qua nút xác nhận (`POST /v1/decisions`).
2. **Không xếp lịch sai luật cứng:** Lịch tạo ra không được đè giờ bận, ngoài giờ rảnh, chồng lên nhau, thiếu giờ nghỉ, quá số phút/ngày hay trễ hạn nộp.
3. **Không lộ dữ liệu nick khác:** Nick nào chỉ được xem và duyệt dữ liệu của đúng nick đó.
4. **Thêm 1 test mới cho lỗi vừa sửa:** Để về sau người khác sửa code không làm lỗi đó sống lại. Nếu có đụng tới cấu trúc dữ liệu/API thì sửa đồng bộ `contracts/`, SQL, Backend và Frontend.

---

## 4. Kiểm tra kỹ lại trên máy mình trước khi báo QA test lại

Sửa code xong, **đừng báo QA liền**. Hãy tự làm 2 bước kiểm tra sau để tránh vừa mở PR đã bị QA trả về:

### Việc 1: Chạy lại đúng cái lỗi vừa sửa **3 lần liên tiếp**
Với lỗi liên quan đến AI/Backend, đổi số cuối từ `--trials 1` thành `--trials 3`:
```bash
python -B docs/qa/f1/run_f1_auto_qa.py --mode live --env-file .env.local --case F1-E01-02 --trials 3
```
*(Tại sao phải chạy 3 lần? Vì AI có lúc trả lời lần 1 trúng, lần 2 trật. Chỉ khi màn hình in ra **`[PASS] 3/3`** cả 3 lần đều đạt thì mới chắc chắn sửa xong thật. Nếu sửa Frontend thì chạy `node docs/qa/f1/run_f1_ui_qa.mjs` thấy hết dòng `[BUG]` là đạt).*

### Việc 2: Chạy bộ kiểm tra chung của dự án xem có lỡ làm hỏng chỗ khác không
Chạy các lệnh tương ứng với phần bạn vừa sửa:
```bash
# Kiểm tra Contract & Backend (nếu sửa Backend/Prompt):
python -B contracts/check_contract.py
python -B backend/scripts/generate_contract_schema_migration.py --check
python -B -m unittest discover -s backend/tests/unit -p "test_*.py"
python -B -m unittest discover -s backend/tests/acceptance_sol -p "test_*.py"
python -B -m unittest discover -s backend/tests/acceptance_api_sol -p "test_*.py"
python -B backend/scripts/evaluate_planner.py

# Kiểm tra Frontend (nếu sửa Frontend):
cd frontend && npx tsc --noEmit && npm run build && npm run format && cd ..

# Kiểm tra Database (nếu sửa file SQL/Migrations — CẤM đụng Cloud phomrutsdhdgejlskwcb!):
supabase db reset --yes && supabase test db
```

### Việc 3: Mở PR và báo QA vào test chốt
- Cập nhật nhật ký vào `worklogs/<ten-github-cua-ban>.md` theo mẫu `worklogs/sample.md`.
- Commit và tiêu đề PR viết bằng **tiếng Anh** (không thêm `Co-Authored-By` hay chữ ký AI).
- Trong phần mô tả PR (viết **tiếng Việt**), ghi rõ bạn vừa sửa Issue nào và dán đoạn kết quả **`[PASS] 3/3`** vừa chạy vào để QA thấy rõ và vào test xác nhận lần cuối.
