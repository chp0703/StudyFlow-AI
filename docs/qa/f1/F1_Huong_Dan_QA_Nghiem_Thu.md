# Hướng dẫn QA Nghiệm thu theo Mã (`fix/f1-qa-acceptance`)

> **Nhánh test:** `fix/f1-qa-acceptance` (kéo mới nhất bằng `git pull origin fix/f1-qa-acceptance`)
>
> **Bảng tick kết quả:** `docs/qa/f1/F1_Bang_Nghiem_Thu_Fix.csv` (import lên Google Sheet, tick cột `QA_da_duyet`)

> **Quy tắc mới — không còn khai báo giờ rảnh.** Hệ thống tự coi mỗi ngày rảnh từ `06:00` đến `22:00` (giờ Việt Nam) và chỉ trừ **giờ bận** cùng các buổi đã xếp. Gõ `"mai t rảnh ..."` không tạo thẻ giờ rảnh: AI trả lời chưa hỗ trợ. Không cần cài giờ rảnh trước khi `"Tìm giờ học"`; muốn chặn khung giờ thì khai báo **giờ bận** (vd `"mai t bận từ 8h đến 12h"`).

---

## 1. Lệnh kéo nhánh & chạy Auto-QA

```bash
# 1. Kéo đúng nhánh về máy
git fetch origin
git checkout fix/f1-qa-acceptance
git pull origin fix/f1-qa-acceptance

# 2. Reset DB local (BẮT BUỘC vì có migration mới — chỉ chạy local, KHÔNG đụng Cloud)
supabase db reset --yes
```

*(Khởi động lại Backend FastAPI + Frontend Vite, sau đó chạy 2 lệnh bên dưới)*

```bash
# 3. Auto-QA Backend + AI DeepSeek thật (32 ca x 3 lượt)
python -B docs/qa/f1/run_f1_auto_qa.py --mode live --env-file .env.local --trials 3

# 4. Auto-QA Frontend + Unit tests
node docs/qa/f1/run_f1_ui_qa.mjs
```

---

## 2. Phân công kiểm tra trên Chrome (`F1-FIX-01` → `F1-FIX-21`)

> **Phát** chạy 2 lệnh Auto-QA ở Mục 1 (và tick luôn `F1-FIX-22`).
>
> **4 bạn còn lại (Hương, Hùng, Kent, Hiển)** chỉ cần kéo nhánh + `supabase db reset --yes` ở Mục 1, bật lại Backend + Frontend rồi làm đúng 5 mục của mình bên dưới trên Chrome.

### Hương (`6` mã — `5` ca Chrome + `1` ca xem kết quả Phần 1)

| Mã lỗi | Thao tác / Câu gõ | Tiêu chí để đạt |
|---|---|---|
| `F1-FIX-01` | Tạo sẵn 1 công việc (không cần cài giờ rảnh), rồi gõ vào Chat: `"xếp lịch học tuần này giúp t với"`. | Hiện thẻ đề xuất lịch bình thường, không còn báo `"Dữ liệu chưa hợp lệ"` hay lỗi `422`. |
| `F1-FIX-02` | Gõ vào Chat: `"Ngày mai học Toán lúc 8h sáng trong 2 tiếng"` (không ghi hạn), bấm Xác nhận rồi xếp lịch. | Tự đặt hạn cuối ngày `23:59` (không bị đặt hạn trùng giờ bắt đầu) và xếp đủ trọn `120 phút` (2 buổi, không mất 30 phút cuối). |
| `F1-FIX-03` | Sau khi đã duyệt 1 buổi học ở ngày mai, gõ tiếp `"Lập lịch học tuần tới"` (hoặc tạo việc mới rồi bấm `"Tìm giờ học"`). | Xếp lịch thành công, không báo lỗi `"Chưa tìm được khung giờ phù hợp"` hay lỗi `422`. |
| `F1-FIX-14` | Không cần bấm tay — xem kết quả chạy Auto-QA Phần 1 của Phát. | Tốc độ trả lời Chat `P95 <= 6 giây`, không lỗi `400` từ AI và web không tự gửi lặp 2 lần. |
| `F1-FIX-15` | Bấm `F12` → tab **Network** → bật **Offline** (tắt mạng). Thử gửi 1 câu chat; sau đó bật mạng tạo 1 thẻ nháp, tắt mạng lại rồi bấm `"Xác nhận"`. | Báo rõ **mất kết nối mạng** (không báo nhầm `"Dịch vụ tạm thời chưa sẵn sàng"`), không mất chữ đã gõ / có nút gửi lại, và mỗi lần bấm chỉ gửi 1 request. |
| `F1-FIX-17` | Chỉnh cửa sổ Chrome cỡ `1366×820`, mở bảng **Công việc** bên phải, rồi chuyển Lịch sang chế độ **Tháng**. | Ô nhập lệnh phía trên vẫn rộng dễ gõ, dòng thông báo không bị ngắt từng chữ một, và Lịch Tháng không che mất nút `"Tuần"`. |

### Hùng (`5` mã Chrome)

| Mã lỗi | Thao tác / Câu gõ | Tiêu chí để đạt |
|---|---|---|
| `F1-FIX-04` | Khai báo giờ bận ngày mai `06:00–19:00` (gõ `"mai t bận từ 6h sáng đến 7h tối"`, Xác nhận). Gõ tạo việc: `"ngày mai 14h học Lý 50 phút, hạn chủ nhật"`, Xác nhận rồi bấm `"Tìm giờ học"`. | Không xếp đúng 14h (đang bận) mà tự dời sang khung trống gần nhất sau đó, trước hạn: `19:00–19:50` ngày mai (không còn báo 0 buổi học), kèm giải thích tiếng Việt trên thẻ. |
| `F1-FIX-05` | Đăng nhập tài khoản A → gõ tạo 1 công việc (chưa bấm Xác nhận) → Đăng xuất A → Đăng nhập tài khoản B trên **cùng trình duyệt Chrome** rồi bấm `F5`. | Tài khoản B hoàn toàn sạch, không nhìn thấy lịch sử chat hay thẻ nháp nào của tài khoản A. |
| `F1-FIX-07` | Mở cùng 1 tài khoản trên **2 tab Chrome song song**, tạo 1 thẻ chờ duyệt để cả 2 tab đều thấy. Bấm `"Xác nhận"` ở Tab 1, ngay sau đó bấm `"Xác nhận"` ở Tab 2. | Tab 1 lưu thành công; Tab 2 báo dữ liệu đã thay đổi và **ẩn/khóa ngay 2 nút `"Xác nhận"` và `"Hủy"`**. |
| `F1-FIX-19` | Vào trang Lịch, đổi khung giờ hiển thị (ví dụ `06:00–22:00`), bấm `"Lưu hiển thị"`. Chuyển sang trang khác rồi quay lại trang Lịch. | Lịch vẫn giữ đúng khung `06:00–22:00` vừa lưu (không tự reset về `08:00–18:00`). |
| `F1-FIX-20` | Khai báo giờ bận kín gần hết ngày (vd bận `06:00–21:00` ngày mai, chỉ còn 1 tiếng trống) rồi tạo việc 3 tiếng hạn tối mai và bấm lập lịch để hiện bảng đề xuất thiếu giờ. | Toàn bộ cảnh báo và lý do chưa xếp đủ giờ đều là **tiếng Việt 100%** (không còn chữ tiếng Anh như `INSUFFICIENT_CAPACITY`, `The greedy baseline...`). |

### Kent (`5` mã Chrome)

| Mã lỗi | Thao tác / Câu gõ | Tiêu chí để đạt |
|---|---|---|
| `F1-FIX-06` | **(1)** Trên trang Lịch gõ câu thiếu thông tin (`"Thêm bài tập Toán"`) → bấm `X` đóng popup → gõ câu mới `"Tìm công việc"`. **(2)** Bấm `F12` → Network → chọn **Slow 3G**, gửi 1 câu tạo việc qua Chat rồi bấm `F5` ngay sau ~0,5 giây. | **(1)** Không bị kẹt lỗi `409`, câu mới không dính giờ/thời lượng của câu cũ. **(2)** Sau khi `F5`, thẻ `"Xác nhận / Hủy"` tự hiện lại để bấm tiếp bình thường. |
| `F1-FIX-08` | Gửi lần lượt 4 câu: `"Học Toán 20h mai 60 phút, hạn 10h sáng mai"`, `"Học Anh 8h sáng mai trong 99999 phút"`, `"Học Sử 8h sáng mai trong 0 phút"`, `"Học Văn 8h sáng mai trong -5 phút"`. | Cả 4 câu đều bị **chặn ngay trước khi hiện thẻ Xác nhận** và báo lỗi tiếng Việt cụ thể (giờ bắt đầu sau hạn, quá giới hạn phút, hoặc thời lượng phải > 0). |
| `F1-FIX-11` | **(1)** Tạo giờ bận 5 ngày liên tiếp (Thứ 2–Thứ 6) rồi bấm Xác nhận lần lượt. **(2)** Gõ câu có 1 vế lỗi + 1 vế tạo việc hợp lệ (`"mai t bận sáng, nhét hộ bài giải tích 2 tiếng tầm 9h nha"`). | **(1)** Không lặp lại 5 lần câu `"Đã cập nhật giờ bận."`. **(2)** Không ghép câu `"Mình chưa hiểu..."` lên đầu thẻ công việc hợp lệ. |
| `F1-FIX-18` | Lưu 1 khung giờ **bận** bắt đầu trước 8h sáng (`06:00–12:00` hoặc `07:00–18:00`), rồi xem trên Lịch tuần (để khung hiển thị mặc định từ `08:00`). Lịch không còn tô nền giờ rảnh. | Nhãn giờ bận vẫn ghi đúng giờ gốc **`06:00–12:00`** (hoặc `07:00–18:00`), không bị cắt chữ thành `08:00–12:00`. |
| `F1-FIX-21` | Bấm `"Xác nhận"` 1 thẻ bất kỳ trong khung Trợ lý AI, sau đó bấm `F5` tải lại trang. | Nhãn góc trên thẻ đổi thành **`"Đã xác nhận"`** (không còn hiện nhầm `"Chờ xác nhận"`). |

### Hiển (`5` mã Chrome)

| Mã lỗi | Thao tác / Câu gõ | Tiêu chí để đạt |
|---|---|---|
| `F1-FIX-09` | Gửi lần lượt 4 câu: **(1)** `"Học Hóa lúc 8r tối nay trong 1 tiếng rưỡi"`, **(2)** `"lm bt toan mai 9h sang nha, 45p"`, **(3)** `"mai t bận sáng, nhét hộ bài giải tích 2 tiếng tầm 9h nha"`, **(4)** Cài sẵn giờ bận `08:00` ngày mai rồi hỏi `"mai t có bận lúc 8h ko"`. | **(1)** Hiểu đúng `20:30` và `90 phút`. **(2)** Hiểu đúng `09:00` ngày mai, `45 phút` (không hỏi lại giờ). **(3)** Tách đủ cả giờ bận và công việc. **(4)** Trả lời đúng là đang bận lúc `08:00` (không báo `"Bạn chưa có kế hoạch"`). |
| `F1-FIX-10` | Gõ `"mai t bận từ 12h trưa tới 8h sáng cùng ngày"` ở **cả 2 nơi** (Trợ lý AI và thanh lệnh trang Lịch). | Cả 2 nơi đều chặn trước khi hiện thẻ, báo rõ `"Giờ kết thúc phải sau giờ bắt đầu."` và không bấm được `"Xác nhận"`. |
| `F1-FIX-12` | Trên thanh lệnh trang Lịch, gõ lần lượt 3 câu để mở popup hỏi thêm: **(1)** `"Học Toán 8h tối mai"`, **(2)** `"Tạo công việc làm bài tập toán vi tích phân trong 2h ngày mai"`, **(3)** `"tạo cv ôn bai đi"`. | **(1)** Hiện `20:00` ngày mai, **để trống** ô thời lượng (không biến `8h` thành `480p` hay tự điền `60p`). **(2)** Điền `120p`, không nhầm giờ thành `02:00 AM`, tiêu đề không dư chữ `"trong"`. **(3)** Tiêu đề sạch, không dư `"cv"`, `"đi"`. |
| `F1-FIX-13` | Copy 1 đoạn chữ dài `8.005` ký tự rồi dán vào **cả 2 ô nhập** (ô Chat ở Trợ lý AI và ô lệnh ở trang Lịch). | Cả 2 ô đều chặn ngay ở `8.000` ký tự trên giao diện (không cho gửi quá `8.000` ký tự lên server). |
| `F1-FIX-16` | Trên trang Lịch thử 3 việc: **(1)** Đang ở tuần hiện tại, bấm tab **Tháng** rồi bấm lại **Tuần**. **(2)** Tạo 3 công việc (xếp ra nhiều hơn 3 buổi học) rồi nhìn số trên nút `"Công việc"`. **(3)** Tạo 2 công việc liên tiếp không chọn màu. | **(1)** Giữ đúng tuần hiện tại (không nhảy lùi về tháng trước). **(2)** Số trên nút `"Công việc"` hiện đúng **3** (đếm theo công việc, không đếm theo buổi học). **(3)** 2 công việc tự mang **2 màu khác nhau**. |

### Ca bổ sung cho quy tắc mới (`F1-FIX-23`) — Hùng

| Mã lỗi | Thao tác / Câu gõ | Tiêu chí để đạt |
|---|---|---|
| `F1-FIX-23` | **(1)** Tài khoản mới, **không** khai báo giờ nào, tạo việc `"Báo cáo hạn thứ sáu 3 tiếng"`, Xác nhận rồi bấm `"Tìm giờ học"`. **(2)** Gõ `"mai t rảnh từ 8h đến 18h"`. **(3)** Sau 21:30, tạo việc 2 tiếng hạn trong hôm nay rồi xếp lịch. **(4)** Mở bảng **Công việc** của việc vừa xếp. | **(1)** Xếp được ngay, mọi buổi nằm trong `06:00–22:00`, không có thông báo `"Chưa có giờ rảnh"` và không có nút `"Thiết lập giờ học mặc định"`. **(2)** Không hiện thẻ giờ rảnh; AI báo chưa hỗ trợ khai báo giờ rảnh. **(3)** Chỉ xếp tới `22:00` (kết quả thiếu giờ, lý do tiếng Việt), không có buổi nào trước giờ hiện tại. **(4)** Trạng thái đúng `"Đã xếp lịch"`. |

---

## 3. Quy tắc tick trên Google Sheet

- **Đạt:** Tick cột `QA_da_duyet`.
- **Chưa đạt:** Bỏ tick `DEV_da_fix`, ghi 1 dòng nguyên nhân (kèm `X-Request-ID` hoặc ảnh) vào cột `Ghi_chu`.
