# Báo cáo Đánh giá Chất lượng Hệ thống

- Đơn vị: Đại học Quốc gia Thành phố Hồ Chí Minh - Trường Đại học Khoa học Tự nhiên - Khoa Công nghệ Thông tin
- Môn học: Tư duy Tính toán (CSC10014) - Đề tài: StudyFlow AI (Tính năng 1: Lập kế hoạch học tập thông minh)
- Nhóm thực hiện (Nhóm 3): Châu Hoà Phát (25127224), Nguyễn Ngọc Thanh Hương (25127197), Nguyễn Trần Minh Khang (25127369), Phạm Hùng Khôi (25127390), Đặng Minh Hùng (25127340), Huỳnh Nguyễn Thế Hiển (25127327)
- Giảng viên hướng dẫn: TS. Châu Thành Đức, TS. Đỗ Đức Hào, ThS. Trần Hoàng Quân
- Thành phố Hồ Chí Minh, tháng 11 năm 2026

---

## Chương 1: Yêu cầu Chức năng (Functional) và Phi chức năng (Non-Functional)

### 1.1 Yêu cầu chức năng

| Mã | Yêu cầu | Kết quả hiện tại |
|---|---|---|
| FR-01 | Người dùng nhập việc cần làm hoặc giờ bận bằng tiếng Việt tự nhiên (có dấu, không dấu, viết tắt, nhiều việc một câu hoặc tự sửa giờ). Thiếu thông tin thì hệ thống mở biểu mẫu hỏi thêm và chỉ lưu sau khi người dùng bấm (Xác nhận). | Chạy đồng bộ giữa khung Chat và trang Lập kế hoạch. Chặn câu nhập quá 8.000 ký tự và xếp hàng đợi nhiều việc trong cùng một câu. |
| FR-02 | Tự xếp và xếp lại lịch học tuần theo giờ bận và hạn chót của từng người. Mặc định khóa khung cố định 06:00 - 22:00 để tránh tự động xếp buổi học vào giờ khuya hoặc rạng sáng (chỉ mở ngoại lệ nếu người dùng ghi rõ giờ sớm hoặc khuya), ưu tiên hạn gần trước, không đè giờ bận và báo rõ phần còn thiếu chỗ. | Tự động áp dụng khung cố định 06:00 - 22:00 (trừ giờ bận), không tự đẩy lịch vào khung 22:00 - 06:00 và không bắt người dùng khai báo thêm. Lịch Tuần hiển thị đủ 00:00 - 24:00, có thẻ gọn cho buổi 25 - 45 phút và nút báo buổi nằm ngoài khung giờ đang xem. |

### 1.2 Yêu cầu phi chức năng

| Mã | Hạng mục | Tiêu chuẩn áp dụng |
|---|---|---|
| NFR-01 | Xếp lịch rule-based nhất quán | Cùng một đầu vào luôn ra đúng một lịch giống nhau. AI chỉ tách thông tin, không tự ý đổi lịch, đè giờ bận hay xếp trễ hạn. |
| NFR-02 | Tốc độ phản hồi | Tải lịch và danh sách việc có độ trễ P95 tối đa 1,0 giây; phản hồi chat có P95 tối đa 6,0 giây; bấm (Xác nhận) hoặc Hủy có P95 tối đa 1,5 giây trong ngưỡng tải hỗ trợ. |
| NFR-03 | An toàn dữ liệu khi ghi | Lưu trọn vẹn giao dịch trong cơ sở dữ liệu. Chặn gửi trùng thao tác và báo xung đột (lỗi 409) nếu dữ liệu đã bị đổi trước khi người dùng bấm duyệt. |
| NFR-04 | Bảo mật và tách tài khoản | Mọi API đều xác thực phiên đăng nhập (JWT), phân quyền tách riêng dữ liệu từng tài khoản ngay trong PostgreSQL (RLS), tách bộ nhớ đệm trình duyệt theo tài khoản và chặn câu lệnh đánh lừa hệ thống. |
| NFR-05 | Phục hồi trạng thái và tiếng Việt | Tải lại trang (F5) giữ nguyên thẻ chờ duyệt hoặc biểu mẫu đang hỏi thêm. Mất mạng sẽ giữ lại câu đã gõ kèm nút Gửi lại; toàn bộ thông báo dùng tiếng Việt. |

---

## Chương 2: Đánh giá mức độ đáp ứng SLA (Service Level Agreement) và SLO (Service Level Objective)

| Hạng mục | Cách đo | SLA (Người dùng) | SLO (Nội bộ) | Kết quả đo thực tế | Đánh giá |
|---|---|---|---|---|---|
| Tải trang và đọc lịch | Gọi liên tiếp API tải lịch và công việc ở mức 1 - 100 CCU | P95 tối đa 1,5 giây (càng thấp càng tốt) | P95 tối đa 1,0 giây (tới 20 CCU) | 1 CCU: 0,10 giây; 10 CCU: 0,16 giây; 20 CCU: 0,54 giây (40 CCU: 2,20 giây) | Đạt (tới 20 CCU) |
| Phản hồi chat AI | Đo từ lúc bấm Gửi đến khi hiện đề xuất qua 50 lượt DeepSeek thật và tải 20 CCU | P95 tối đa 8,0 giây (càng thấp càng tốt) | P95 tối đa 6,0 giây | P50 = 1,85 giây; P95 = 4,89 giây; Max = 6,25 giây (20 CCU: P95 = 3,11 giây) | Đạt |
| Lưu khi bấm (Xác nhận) hoặc Hủy | Đo trực tiếp API lưu quyết định khi thử toàn luồng và tải 1 - 50 CCU | P95 tối đa 2,0 giây (càng thấp càng tốt) | P95 tối đa 1,5 giây (tới 10 CCU) | Toàn luồng: 0,80 giây; 10 CCU: 0,69 giây (20 CCU: 1,62 giây - vẫn đạt SLA) | Đạt (tới 10 CCU) |
| Lịch không xung đột | Kiểm tra đè giờ bận, chồng lịch, trễ hạn trên 650 lượt mô phỏng và 34 bài E2E | 0% vi phạm (100% lịch đã lưu hợp lệ) | 0% vi phạm rule-based | 0% vi phạm qua 500 lượt mô phỏng chuẩn, 150 lượt tải 5 - 200 việc và 34/34 bài E2E | Đạt |
| Quyền duyệt dữ liệu | Gửi câu chat thường và câu lệnh đánh lừa AI mà không bấm (Xác nhận) | 0% thay đổi dữ liệu trước khi bấm (Xác nhận) | 0% thao tác ghi ngoài bước duyệt | 0% ghi trái phép trên toàn bộ kịch bản kiểm thử bảo mật và đánh lừa hệ thống | Đạt |
| Hiểu tiếng Việt ổn định | Chạy lặp 3 lần độc lập mỗi dạng câu (Pass^3) trên 6 nhóm câu với DeepSeek thật | Tách đúng tối thiểu 90% câu đủ thông tin; câu mơ hồ hỏi lại trước khi lưu | Pass^3 tối thiểu 85% (khoảng 95% mỗi lượt) | 6/6 nhóm đạt 3/3 (18/18 lượt đúng, 100%): chuẩn, không dấu, viết tắt, 8r, 10h kém 15, tự sửa giờ | Đạt |
| Tách biệt tài khoản | Gọi API với mã phiên sai, đọc chéo đề xuất người khác và đổi tài khoản cùng máy | 0% rò rỉ lịch hoặc bản nháp giữa các tài khoản | 0% truy cập chéo lọt qua | 0% rò rỉ: chặn 100% mã phiên sai (401), chặn truy cập chéo (403/404) và tách cache | Đạt |
| Tỷ lệ lỗi 5xx và 503 | Thống kê mã lỗi trên 50 lượt toàn luồng và các mức tải đọc, ghi, chat | Tối đa 2,0% (càng thấp càng tốt) | Tối đa 1,0% trong ngưỡng tải hỗ trợ | Toàn luồng: 0/50 (0%); đọc 100 CCU: 0%; chat 20 CCU: 0%; ghi tới 30 CCU: 0% (50 CCU: 1,96%) | Đạt (tới 30 CCU) |

Lưu ý: SLA không áp dụng khi thiết bị người dùng mất mạng, dịch vụ bên thứ ba (DeepSeek API, Supabase Cloud) gặp sự cố hoặc trong khung giờ bảo trì có báo trước.

---

## Chương 3: Kết quả Kiểm thử (Testing) và Mô phỏng (Simulation)

### 3.1 Tổng hợp 7 tầng kiểm thử

| Tầng kiểm thử | Phạm vi kiểm tra | Kết quả |
|---|---|---|
| Đặc tả API và Schema | Kiểm tra đồng bộ đặc tả OpenAPI, cấu trúc JSON Schema và cơ sở dữ liệu (258 định nghĩa, 9 API, 9 công cụ AI, 172 mẫu dữ liệu, 60 tệp migration) | Đạt 100% |
| Cơ sở dữ liệu (pgTAP) | Kiểm tra phân quyền từng tài khoản (RLS), hàm ghi dữ liệu và ràng buộc bảng | 799/799 đạt (25 tệp) |
| Ghi đồng thời | Kiểm tra khóa dòng khi nhiều yêu cầu ghi cùng lúc, hết hạn nháp và hoàn tác khi lỗi | 9/9 đạt |
| Backend (Python) | Unit test (28 tệp), kiểm thử thuật toán xếp lịch (4), kiểm thử API (8), tích hợp (2) | 400/400 đạt (267 unit, 38 thuật toán, 79 API, 16 tích hợp) |
| Frontend (React) | Kiểm tra kiểu TypeScript, đóng gói build (1,83 giây), unit test (33 tệp) và kiểm thử giao diện tự động | Đạt (157/157 unit và 5/5 kiểm thử giao diện) |
| Kiểm thử toàn luồng E2E | Chạy đủ hệ thống thật gồm Backend, Supabase và DeepSeek API (50 lượt chat) | 34/34 đạt (0 lỗi, P95 = 4891,7 ms) |
| Trình duyệt Chrome | Kiểm tra trực tiếp thẻ buổi học ngắn, nút báo buổi ngoài khung khi cuộn, F5 và biểu mẫu hỏi thêm | Đạt (0 lỗi dữ liệu 422, lỗi máy chủ 5xx hay lỗi giao diện) |

### 3.2 10 tình huống kiểm thử tự động tiêu biểu

Trong 34 tình huống kiểm thử toàn luồng (đạt 34/34), nhóm chạy lặp 10 lượt độc lập cho 9 tình huống chức năng - bảo mật tiêu biểu (tổng 90/90 lượt đạt, 120 lượt gọi DeepSeek thật, 0 lỗi 503) cùng 50 lượt đo độ trễ AI liên tiếp.

| STT | Đầu vào QA kiểm thử (Input) | Mục tiêu kiểm tra | Kết quả thực tế |
|---|---|---|---|
| 1 | "Ngày mai tôi muốn ôn Giải tích lúc 9h sáng trong 60 phút, ưu tiên cao.", bấm (Xác nhận), rồi nhập "Hãy lập lịch học cho tuần này.", bấm (Xác nhận) | Tạo việc qua chat và tự xếp đúng khung giờ người dùng chỉ định | Đạt 10/10 - Cả 10 lượt đều lưu đúng 1 việc 60 phút (ưu tiên cao) và xếp đúng khung 09:00 - 10:00 ngày mai. |
| 2 | "Ngày mai tôi muốn học Toán lúc 8h sáng trong 2 tiếng, ưu tiên cao.", bấm (Xác nhận), rồi nhập "Hãy lập lịch học cho tuần này giúp tôi.", bấm (Xác nhận) | Tự tách buổi dài vượt trần 90 phút và gán hạn chót mặc định khi thiếu hạn | Đạt 10/10 - Tự lấy hạn cuối ngày (23:59) và tách thành 2 buổi học nối tiếp đủ 120/120 phút ở cả 10 lượt. |
| 3 | Có sẵn buổi đã duyệt ở tuần này và việc ở tuần tới; nhập "Sắp xếp lại lịch tuần tới.", bấm (Xác nhận) | Xếp lại lịch tuần tới mà không làm xáo trộn lịch tuần hiện tại | Đạt 10/10 - Sinh lịch mới cho tuần tới thành công, giữ nguyên buổi học cũ của tuần này ở cả 10 lượt. |
| 4 | Đã có giờ bận 09:00 - 10:00 ngày mai; tạo việc 60 phút từ 08:00 (hạn 12:00) rồi yêu cầu lập lịch | Tránh tuyệt đối khung giờ bận đã lưu theo nguyên tắc rule-based | Đạt 10/10 - Không xếp đè vào 09:00 - 10:00, chỉ xếp vào khung giờ trống hợp lệ ở cả 10 lượt. |
| 5 | Gửi yêu cầu khi thiếu hoặc sai mã đăng nhập; dùng tài khoản B đọc và duyệt đề xuất của tài khoản A | Bảo mật xác thực phiên đăng nhập và chặn truy cập chéo tài khoản | Đạt 10/10 - Chặn mã sai (401), chặn tài khoản B xem/duyệt lịch tài khoản A (403/404), không rò rỉ. |
| 6 | "Thêm bài tập Giải tích" (hệ thống mở biểu mẫu hỏi thêm), bấm Hủy, rồi nhập "Tìm các công việc hiện có." | Cho phép hủy giữa bước hỏi thêm để chat tiếp không bị kẹt | Đạt 10/10 - Hủy bản nháp ngay lập tức và trả lời câu kế tiếp bình thường (không kẹt lỗi 409). |
| 7 | Tạo 1 đề xuất lập lịch rồi gửi đồng thời 2 yêu cầu bấm (Xác nhận) cùng lúc (giả lập 2 tab) | Chặn lưu trùng hoặc ghi đè khi bấm duyệt đồng thời từ nhiều tab | Đạt 10/10 - Đúng 1 yêu cầu thành công (200), yêu cầu kia bị từ chối vì dữ liệu đã cũ (409) ở cả 10 lượt. |
| 8 | Lần lượt nhập 4 câu sai: "25h ngày mai", "trong 0 phút", "trong -5 phút", "hạn chót hôm qua" | Kiểm tra và chặn sớm dữ liệu bất hợp lệ trước khi tạo lịch | Đạt 10/10 - Chặn cả 4 trường hợp trước bước lưu ở cả 10 lượt, không tạo việc sai và không lỗi máy chủ (500). |
| 9 | "Học Hóa lúc 8r tối mai trong 1 tiếng rưỡi" (gửi lặp 10 lần độc lập) | Hiểu đúng tiếng Việt khẩu ngữ, viết tắt và thời lượng quy đổi | Đạt 10/10 - Cả 10 lần đều tách chính xác 20:30 ngày mai và thời lượng 90 phút. |
| 10 | Chuỗi 50 lượt chat tiếng Việt thực tế gọi liên tiếp qua mô hình DeepSeek | Đo tốc độ phản hồi và tỷ lệ lỗi quá tải 503 ở luồng AI thật | Đạt 50/50 - P50 = 1849,4 ms, P95 = 4891,7 ms (dưới ngưỡng 6,0 giây), 0/50 lỗi 503. |

### 3.3 Mô phỏng bộ lập lịch

Nhóm chạy 500 lượt trên 5 kịch bản chuẩn và 150 lượt thử tải 14 ngày từ 5 đến 200 công việc trực tiếp trên thuật toán xếp lịch (chưa tính độ trễ mạng và AI).

| Kịch bản mô phỏng | Coverage | Vi phạm | P50 (ms) | P95 (ms) | P99 (ms) | Plans/s |
|---|---|---|---|---|---|---|
| Chuẩn: Lịch đơn không có giờ bận (100 lượt) | FULL | 0 | 0,187 | 0,217 | 0,300 | 5105 |
| Chuẩn: Lịch tách qua khung giờ bận (100 lượt) | FULL | 0 | 0,211 | 0,259 | 0,346 | 4662 |
| Chuẩn: Thiếu quỹ giờ trống (100 lượt) | PARTIAL | 0 | 0,149 | 0,185 | 0,244 | 6321 |
| Chuẩn: Giữ nguyên buổi đã xếp sẵn (100 lượt) | FULL | 0 | 0,244 | 0,429 | 0,702 | 3540 |
| Chuẩn: Ưu tiên hạn sớm trước độ ưu tiên (100 lượt) | PARTIAL | 0 | 0,177 | 0,210 | 0,262 | 5568 |
| Tải 14 ngày: 5 công việc (30 lượt) | FULL | 0 | 5,811 | 6,229 | 6,293 | 171,6 |
| Tải 14 ngày: 50 công việc (30 lượt) | FULL | 0 | 95,156 | 132,329 | 139,230 | 10,1 |
| Tải 14 ngày: 100 công việc (30 lượt) | PARTIAL | 0 | 314,987 | 411,912 | 430,901 | 3,0 |
| Tải 14 ngày: 200 công việc (30 lượt) | PARTIAL | 0 | 530,026 | 771,431 | 804,532 | 1,8 |

*Chú thích: Plans/s là số phương án lịch hoàn chỉnh mà thuật toán tính xong trong 1 giây trên CPU (càng cao càng nhanh). Coverage cho biết mức xếp kín thời lượng: FULL là xếp đủ 100%; PARTIAL xuất hiện ở các kịch bản cố tình tạo tổng việc vượt quỹ giờ trống nên thuật toán xếp tối đa trong phần còn trống và báo rõ phần thiếu (đúng thiết kế, 0 vi phạm).*

### 3.4 Kiểm thử tải nhiều người dùng cùng lúc

Đo trên máy Windows 12 luồng CPU, 7,68 GB RAM, chạy 1 tiến trình máy chủ (worker FastAPI) cùng cơ sở dữ liệu Supabase cục bộ. Mục tiêu SLO độ trễ áp dụng theo Chương 2: luồng đọc tối đa 1,0 giây, luồng ghi tối đa 1,5 giây, luồng chat AI tối đa 6,0 giây.

| Luồng | CCU | Thành công (Đạt/Tổng) | Lỗi (%) | Thông lượng (req/s) | P50 (ms) | P95 (ms) | So với SLO |
|---|---|---|---|---|---|---|---|
| Luồng đọc | 1 | 118/118 req 2xx | 0,00% | 14,70 | 67,14 | 97,47 | Đạt (dưới 1s) |
| Luồng đọc | 10 | 604/604 req 2xx | 0,00% | 74,64 | 114,67 | 163,54 | Đỉnh tải - Đạt |
| Luồng đọc | 20 | 603/603 req 2xx | 0,00% | 74,46 | 229,27 | 540,97 | Đạt |
| Luồng đọc | 40 | 408/408 req 2xx | 0,00% | 47,04 | 685,77 | 2204,54 | Vượt SLO |
| Luồng đọc | 100 | 547/547 req 2xx | 0,00% | 59,54 | 1141,41 | 4401,80 | Vượt SLO (0% lỗi) |
| Luồng ghi và duyệt | 1 | 9/9 lượt lưu | 0,00% | 2,11 | 319,39* | 496,94* | Đạt (dưới 1,5s) |
| Luồng ghi và duyệt | 10 | 60/60 lượt lưu | 0,00% | 13,84 | 548,93* | 691,25* | Đỉnh tải - Đạt |
| Luồng ghi và duyệt | 20 | 60/60 lượt lưu | 0,00% | 12,72 | 1160,06* | 1615,61* | Vượt SLO |
| Luồng ghi và duyệt | 30 | 60/60 lượt lưu | 0,00% | 11,32 | 1876,79* | 3080,93* | Vượt SLO |
| Luồng ghi và duyệt | 50 | 50/51 lượt lưu | 1,96% | 8,51 | 4024,93* | 6177,63* | Vượt SLO (có lỗi) |
| Luồng chat AI | 1 | 1/1 lượt chat | 0,00% | 0,41 | 2432,49 | 2432,49 | Đạt (dưới 6s) |
| Luồng chat AI | 10 | 10/10 lượt chat | 0,00% | 3,27 | 1867,01 | 3054,30 | Đạt |
| Luồng chat AI | 20 | 20/20 lượt chat | 0,00% | 5,98 | 2822,21 | 3106,05 | Đạt (Max 3,34s) |

*Chú thích: Thông lượng (req/s) là số yêu cầu HTTP xử lý xong mỗi giây. Ở luồng đọc, req 2xx là số yêu cầu tải danh sách việc, lịch và khung giờ trả thành công trong khoảng 8 giây. Ở luồng ghi và duyệt, mỗi lượt lưu gồm 2 yêu cầu nối tiếp (tạo đề xuất rồi bấm (Xác nhận) lưu cơ sở dữ liệu, nên đỉnh 13,84 req/s tại 10 CCU tương ứng 6,92 lượt lưu mỗi giây); dấu * là độ trễ đo riêng tại bước bấm (Xác nhận). Ở luồng chat AI, mỗi người dùng gửi đồng thời 1 câu tiếng Việt qua DeepSeek thật (lượt chat = phản hồi 200 OK).*

Với cấu hình 1 worker cục bộ, hệ thống chạy ổn trong SLO tới 20 CCU đọc hoặc chat và 10 CCU ghi; vượt mốc này yêu cầu phải chờ hàng đợi nên P95 tăng nhanh. Khi đưa lên máy chủ nhiều worker, nhóm cần đo lại để xác định ngưỡng tải mới.

---

## Chương 4: Đánh giá Hệ thống (System Evaluation)

### 4.1 So sánh trước và sau khi tối ưu

| Chỉ số | Trước tối ưu | Sau tối ưu tốc độ | Bản hiện tại |
|---|---|---|---|
| Kiểm thử toàn luồng E2E | 33/34 đạt (1 lỗi) | 34/34 đạt (0 lỗi) | 34/34 đạt (0 lỗi) |
| Độ trễ Chat P50 / P95 / Max (ms) | 2747,8 / 6691,0 / 11139,0 | 1959,9 / 2941,8 / 4064,2 | 1849,4 / 4891,7 / 6245,8 |
| Độ trễ bấm (Xác nhận) P95 (ms) | 645,5 | 753,3 | 800,9 |
| Hiểu tiếng Việt ổn định (Pass^3) | 6/6 nhóm đạt 3/3 | 6/6 nhóm đạt 3/3 | 6/6 nhóm đạt 3/3 (100%) |
| Trạng thái lỗi QA | Còn lỗi tốc độ và giao diện | Còn 4 lỗi giao diện Chrome và câu "2h mai" | Đã sửa 25/25 lỗi QA (0 lỗi tồn đọng) |

*Ghi chú: Ở bản hiện tại, độ trễ trung vị (P50) giảm xuống 1849,4 ms; P95 dao động trong khoảng 2,9 - 4,9 giây giữa hai đợt đo do tải tức thời của dịch vụ bên ngoài DeepSeek API và vẫn nằm gọn dưới ngưỡng SLO 6,0 giây.*

### 4.2 Năm nhóm lỗi điển hình đã sửa và ảnh minh họa

| Mã lỗi | Lỗi cũ | Cách sửa và kết quả |
|---|---|---|
| F1-FIX-14 | Chat phản hồi chậm 6,7 - 11,1 giây (P95 = 6691 ms). | Giảm mức suy luận của model về thấp, bỏ lượt đọc thừa lúc đầu, lưu đệm khóa xác thực JWT và giữ kết nối HTTP mở. P95 giảm còn 2,94 - 4,89 giây. |
| F1-FIX-06 | Tải lại trang (F5) hoặc đóng hộp thoại hỏi thêm gây kẹt lỗi xung đột 409. | Trả sẵn mã xác nhận ngay ở bước hỏi thêm để hủy được lập tức và tải lại đủ trạng thái từ máy chủ sau F5 (xác minh đạt 10/10 ở dòng 6 Bảng 3.2). |
| F1-FIX-12 | Câu "hoc vtp 2h mai" bị tính trùng giờ bắt đầu (02:00 sáng khuya) và thời lượng; ô phút tự điền 60. | Chặn tính trùng, để trống ô phút kèm gợi ý "Ví dụ: 60" và giữ khung tự xếp cố định 06:00 - 22:00 để tránh xếp lịch khuya (Hình 4.1 - 4.2). |
| F1-FIX-03 | Xếp lại lịch tuần tới bị lỗi 422; nhắn lúc rạng sáng giờ Việt Nam bị lệch ngày. | Khóa khung mặc định 06:00 - 22:00 tránh xếp khuya, vẫn mở ngoại lệ cho giờ ghi rõ và gửi múi giờ +07:00 (đạt 10/10, dòng 3 Bảng 3.2). |
| F1-FIX-23, 24 | Thẻ buổi học 25 - 45 phút bị cắt chữ; buổi nằm ngoài khung đang xem bị khuất. | Hiển thị thẻ gọn một dòng cho buổi ngắn và ghim nút "2 buổi ngoài khung - Hiện" trên đầu cột ngày (Hình 4.3 - 4.5). |

![Hình 4.1: Biểu mẫu hỏi thêm khi nhập hoc vtp 2h mai trên Chrome](figures/fig_clarify_2h_mai.png)

![Hình 4.2: Biểu mẫu hỏi thêm khi nhập hoc vtp 2h chieu mai trên Chrome](figures/fig_clarify_2h_chieu_mai.png)

![Hình 4.3: Thẻ gọn một dòng giúp buổi học 25 - 45 phút hiển thị đủ chữ (F1-FIX-23)](figures/fig_compact_cards.png)

![Hình 4.4: Nút báo buổi ngoài khung ghim cố định trên tiêu đề ngày khi cuộn lịch (F1-FIX-24)](figures/fig_out_of_range_pill.png)

![Hình 4.5: Bấm nút báo tự mở rộng khung giờ để hiện đủ hai buổi học 17:30 và 20:30 (F1-FIX-24)](figures/fig_out_of_range_expanded.png)

### 4.3 Đánh giá mức độ hữu ích

Tính năng 1 đổi một câu tiếng Việt bình thường thành lịch học tuần trong 1,8 - 4,9 giây. Qua 650 lượt mô phỏng và 34/34 bài kiểm thử toàn luồng với DeepSeek thật, bộ lập lịch không vi phạm giờ bận hay hạn chót lần nào.

---

## Chương 5: Rủi ro tồn đọng và Kế hoạch hành động

Hệ thống đã chạy ổn trong đợt kiểm thử nội bộ, nhưng vẫn còn một số giới hạn nhỏ và việc cần hoàn thiện tiếp.

| Hạn chế / Việc cần làm | Mức ưu tiên | Hướng xử lý và kiểm tra |
|---|---|---|
| 1. Cho 12 - 20 sinh viên ngoài nhóm dùng thử thật (hiện mới chỉ có thành viên nhóm tự kiểm tra). | Quan trọng | Thu đủ 12 - 20 phiếu đánh giá từ sinh viên thật, ghi rõ thời gian làm xong 5 tác vụ cơ bản và điểm đánh giá độ dễ dùng (SUS). |
| 2. Vùng xem lịch trên màn hình laptop phổ thông (1366x820) hơi bị thu hẹp khi mở đồng thời ô nhập lệnh, thanh đề xuất hoặc hộp thoại hỏi thêm. | Trung bình | Tinh gọn bố cục thanh công cụ và vị trí hộp thoại ở kích thước 1366x820, rồi kiểm tra lại trên trình duyệt bảo đảm vùng lịch thoáng và hiển thị đủ. |
| 3. Độ trễ phản hồi chat AI và ngưỡng tải đồng thời vẫn còn dư địa cải thiện khi triển khai rộng hơn. | Trung bình | Tinh gọn cấu hình suy luận của mô hình, gộp bước gọi dữ liệu nội bộ và đo lại P95 khi chạy nhiều tiến trình máy chủ. |
| 4. Tiêu đề công việc tách từ câu chat không dấu hoặc viết tắt vẫn giữ nguyên dạng thô (ví dụ nhập "hoc vtp" chưa tự chuẩn hóa thành "Học VTP") và một số cách diễn đạt như nhắc hạn nộp hoặc hỏi chi tiết lịch ngay trong chat chưa xử lý thật tự nhiên. | Trung bình | Bổ sung bước chuẩn hóa tiêu đề (viết hoa, khôi phục dấu và từ viết tắt phổ biến) và tinh chỉnh phân tách hạn nộp, câu hỏi xem lịch trong bộ phân tích ngôn ngữ. |
