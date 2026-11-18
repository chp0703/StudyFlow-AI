# Chạy demo trên máy local

Dùng Supabase **local** (Docker). Không dùng dự án cloud `phomrutsdhdgejlskwcb`. Chạy từ thư mục gốc repo, trong Git Bash/WSL/macOS/Linux.

Cần: Docker Desktop, Supabase CLI, Python 3.12+, Node 22, `psql`, `openssl`. Muốn dùng trợ lý chat hoặc sinh câu hỏi F2 thì cần thêm `DEEPSEEK_API_KEY` của riêng bạn; không có key thì chỉ các endpoint có cấu trúc chạy, `POST /v1/messages` trả 503.

## 1. Database

```bash
python -m pip install -r backend/requirements.txt
supabase start
supabase db reset --yes
supabase status          # lấy "Publishable" key (sb_publishable_...) và API URL
```

## 2. Khóa ký RPC

Sinh một secret ngẫu nhiên, đăng ký vào DB và giữ lại cùng giá trị cho backend:

```bash
SECRET_HEX=$(openssl rand -hex 32)
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
  -v key_id=f1-dev-1 -v secret_hex="$SECRET_HEX" -f supabase/scripts/register_dev_key.sql
export RPC_SIGNING_KEY_ID=f1-dev-1
export RPC_SIGNING_SECRET_BASE64=$(printf '%s' "$SECRET_HEX" | xxd -r -p | base64)
```

Khóa hết hạn sau 30 ngày; chạy lại bước này nếu backend báo khóa không hợp lệ.

## 3. Backend

```bash
export SUPABASE_URL=http://127.0.0.1:54321
export SUPABASE_PUBLISHABLE_KEY=<publishable key từ supabase status>
export CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export DEEPSEEK_API_KEY=<tùy chọn>
uvicorn backend.app.main:create_app --factory --port 8000
```

Backend chỉ đọc biến môi trường của shell, không tự đọc `.env.local`.

## 4. Frontend

```bash
cd frontend
cat > .env.local <<'ENV'
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable key từ supabase status>
ENV
npm install
npm run dev
```

Mở http://localhost:5173. Thiếu một trong ba biến `VITE_*` thì app chạy chế độ demo (không đăng nhập, dữ liệu trong bộ nhớ).

## 5. Tài khoản

Đăng ký bằng form đăng nhập của app, hoặc tạo bằng lệnh (email/mật khẩu tùy chọn):

```bash
curl -s http://127.0.0.1:54321/auth/v1/signup -H "apikey: <publishable key>" \
  -H "Content-Type: application/json" -d '{"email":"demo@example.test","password":"<mật khẩu>"}'
```

`.env.local` và mọi khóa nằm ngoài Git (`.env*` đã được gitignore).
