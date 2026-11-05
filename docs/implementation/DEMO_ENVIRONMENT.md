# Chuẩn bị môi trường demo F1

Backend chạy trên máy; Supabase Auth/DB và DeepSeek cần cấu hình thật để nghiệm thu live. Không gửi API key, mật khẩu hoặc access token vào chat.

## 1. Supabase project đã tham gia

Người dùng cung cấp project ref `phomrutsdhdgejlskwcb` sau khi tham gia StudyFlow-AI. Project URL tương ứng đã điền trong `.env.example`. Chưa kiểm tra schema/migration history hoặc quyền quản trị; không coi project vừa tham gia là DB trống. Phải đọc migration history và inventory trước khi áp dụng migration; không reset dữ liệu cloud.

1. Mở [Supabase Dashboard](https://supabase.com/dashboard), đăng nhập bằng tài khoản của bạn và chọn project StudyFlow-AI có ref `phomrutsdhdgejlskwcb`. Xác định project demo hay project chung của nhóm và quyền hiện có; giữ database password trong nơi riêng tư.
2. Khi project sẵn sàng, lấy Project URL và publishable API key từ phần cấu hình API của project. Không dùng secret/service-role key thay publishable key cho request người dùng.
3. Public JWKS của project đã được kiểm tra ngày 05/11/2026: HTTP 200 với một key ES256. Điều này chỉ xác nhận signing metadata công khai, chưa chứng minh quyền DB hoặc toàn bộ luồng đăng nhập. Không rotate/chuyển key của project dùng chung chỉ để khớp mẫu. Backend phải kiểm tra chữ ký, issuer của project và audience authenticated; cấu hình phải theo signing key thực tế nếu project đổi key sau này.
4. Sao chép `.env.example` thành `.env.local` ở thư mục gốc repo. Điền SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_PROJECT_REF và SUPABASE_DB_PASSWORD. Các file .env thực tế đã được ignore.
5. Phần migration/key provisioning và kiểm tra grants sẽ do Sol thực hiện sau khi code qua CI. Không chạy reset trên project cloud. Backend chỉ dùng user JWT; administrative credentials chỉ dành cho deployment/test tooling.
6. Tạo hai tài khoản demo tổng hợp trong Supabase Auth hoặc bằng công cụ seed admin được bàn giao sau. Hai tài khoản dùng để kiểm tra cách ly dữ liệu; không dùng tài khoản cá nhân trong fixture.

RPC_SIGNING_SECRET_BASE64 là secret riêng giữa backend và DB, không phải Supabase JWT secret và không phải DeepSeek API key. Sol sẽ tạo key ngẫu nhiên và cung cấp đường provisioning kín; không ghi key vào migration hoặc log. Key chưa được cấu hình phải khiến mutation fail closed.

## 2. DeepSeek

1. Mở [DeepSeek Platform](https://platform.deepseek.com/), đăng nhập và tạo API key cho demo. Tài khoản cần có quyền sử dụng API.
2. Điền DEEPSEEK_API_KEY vào `.env.local`. Giữ DEEPSEEK_BASE_URL=https://api.deepseek.com và DEEPSEEK_MODEL=deepseek-flash theo adapter dự kiến.
3. Gemini/Antigravity chỉ dùng để phát triển; key Gemini không thay key DeepSeek của ứng dụng.

## 3. Báo sẵn sàng

Sau khi điền xong, chỉ cần báo “đã cấu hình .env.local”; không gửi nội dung file. Sol sẽ kiểm tra sự hiện diện của biến, chạy preflight với giá trị được che và báo kết quả. Khi chưa có cấu hình thật, CI/unit tests vẫn chạy được nhưng G3 giữ trạng thái chưa nghiệm thu.

Tham khảo: [Supabase JWT](https://supabase.com/docs/guides/auth/jwts), [DeepSeek API](https://api-docs.deepseek.com/).
