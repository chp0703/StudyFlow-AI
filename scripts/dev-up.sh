#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.dev-runtime"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
SUPABASE_LOG="$RUNTIME_DIR/supabase.log"
FRONTEND_URL="http://127.0.0.1:5173"
BACKEND_URL="http://127.0.0.1:8000"
BACKEND_PID=""
FRONTEND_PID=""

mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"
umask 077

say() {
  printf '[StudyFlow] %s\n' "$1"
}

die() {
  printf '[StudyFlow] ERROR: %s\n' "$1" >&2
  exit 1
}

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for command_name in docker supabase python3 npm curl openssl lsof; do
  command -v "$command_name" >/dev/null 2>&1 || die "Thiếu lệnh $command_name."
done

if ! docker info >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    say "Đang mở Docker Desktop..."
    open -a Docker
    for _ in {1..90}; do
      docker info >/dev/null 2>&1 && break
      sleep 2
    done
  fi
  docker info >/dev/null 2>&1 || die "Docker chưa sẵn sàng. Hãy mở Docker Desktop rồi chạy lại."
fi

[[ -f "$ROOT_DIR/.env.local" ]] || die "Thiếu $ROOT_DIR/.env.local. Sao chép từ .env.example và điền DeepSeek/RPC secrets."
set -a
# shellcheck disable=SC1091
source "$ROOT_DIR/.env.local"
set +a

for variable_name in DEEPSEEK_API_KEY RPC_SIGNING_KEY_ID RPC_SIGNING_SECRET_BASE64; do
  [[ -n "${!variable_name:-}" ]] || die "Thiếu $variable_name trong .env.local."
done

say "Đang khởi động Supabase local..."
if ! (cd "$ROOT_DIR" && supabase start >"$SUPABASE_LOG" 2>&1); then
  die "Supabase không khởi động được. Xem $SUPABASE_LOG"
fi

SUPABASE_STATUS_FILE="$RUNTIME_DIR/supabase.env"
(cd "$ROOT_DIR" && supabase status -o env >"$SUPABASE_STATUS_FILE" 2>>"$SUPABASE_LOG") \
  || die "Không đọc được Supabase status. Xem $SUPABASE_LOG"
# shellcheck disable=SC1090
source "$SUPABASE_STATUS_FILE"
SUPABASE_URL="${API_URL:?Supabase status thiếu API_URL}"
SUPABASE_PUBLISHABLE_KEY="${PUBLISHABLE_KEY:-${ANON_KEY:-}}"
[[ -n "$SUPABASE_PUBLISHABLE_KEY" ]] || die "Supabase status thiếu publishable key."
export SUPABASE_URL SUPABASE_PUBLISHABLE_KEY
export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

case "$SUPABASE_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) die "Từ chối chạy với Supabase không phải local: $SUPABASE_URL" ;;
esac

cat >"$ROOT_DIR/frontend/.env.local" <<ENV
VITE_API_BASE_URL=$BACKEND_URL
VITE_SUPABASE_URL=$SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY=$SUPABASE_PUBLISHABLE_KEY
ENV

SECRET_HEX="$(printf '%s' "$RPC_SIGNING_SECRET_BASE64" | python3 -c 'import base64,sys; print(base64.b64decode(sys.stdin.read(), validate=True).hex())')" \
  || die "RPC_SIGNING_SECRET_BASE64 không hợp lệ."
[[ ${#SECRET_HEX} -ge 64 ]] || die "RPC signing secret phải có ít nhất 32 byte."
PROJECT_ID="$(awk -F'"' '/^project_id = / {print $2; exit}' "$ROOT_DIR/supabase/config.toml")"
[[ -n "$PROJECT_ID" ]] || die "Không đọc được project_id Supabase local."
DB_CONTAINER="supabase_db_${PROJECT_ID}"
docker inspect "$DB_CONTAINER" >/dev/null 2>&1 \
  || die "Không tìm thấy container database $DB_CONTAINER."
docker exec -i "$DB_CONTAINER" psql -U postgres -v ON_ERROR_STOP=1 \
  -v key_id="$RPC_SIGNING_KEY_ID" -v secret_hex="$SECRET_HEX" >/dev/null <<'SQL'
insert into app_private.rpc_attestation_keys (key_id, key_material, not_before, not_after)
values (:'key_id', decode(:'secret_hex', 'hex'), now() - interval '1 hour', now() + interval '30 days')
on conflict (key_id) do update
set key_material = excluded.key_material,
    not_before = excluded.not_before,
    not_after = excluded.not_after;
SQL
unset SECRET_HEX

DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}"
DEEPSEEK_HTTP_CODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" "${DEEPSEEK_BASE_URL%/}/models")" \
  || die "Không kết nối được DeepSeek API."
[[ "$DEEPSEEK_HTTP_CODE" == "200" ]] || die "DeepSeek API key không hợp lệ (HTTP $DEEPSEEK_HTTP_CODE)."
say "DeepSeek API key hợp lệ."

for port in 8000 5173; do
  if lsof -n -P -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    die "Port $port đang được dùng. Hãy dừng tiến trình cũ rồi chạy lại."
  fi
done

if [[ ! -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  say "Đang tạo Python virtual environment..."
  python3 -m venv "$ROOT_DIR/.venv"
  "$ROOT_DIR/.venv/bin/python" -m pip install -q -r "$ROOT_DIR/backend/requirements.txt"
fi
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  say "Đang cài frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

say "Đang bật FastAPI..."
(cd "$ROOT_DIR" && "$ROOT_DIR/.venv/bin/uvicorn" backend.app.main:create_app --factory \
  --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1) &
BACKEND_PID=$!

say "Đang bật Vite..."
(cd "$ROOT_DIR/frontend" && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort \
  >"$FRONTEND_LOG" 2>&1) &
FRONTEND_PID=$!

wait_for_http() {
  local url="$1"
  local expected="$2"
  local label="$3"
  local code
  for _ in {1..60}; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 "$url" 2>/dev/null || true)"
    if [[ "$code" == "$expected" ]]; then
      return 0
    fi
    sleep 1
  done
  die "$label chưa sẵn sàng. Xem log trong $RUNTIME_DIR"
}

wait_for_http "$SUPABASE_URL/auth/v1/health" "200" "Supabase Auth"
wait_for_http "$BACKEND_URL/v1/tasks" "401" "FastAPI"
wait_for_http "$FRONTEND_URL" "200" "Vite"

say "Sẵn sàng:"
printf '  Web:      %s\n' "$FRONTEND_URL"
printf '  API:      %s\n' "$BACKEND_URL"
printf '  Supabase: %s\n' "$SUPABASE_URL"
printf '  Studio:   http://127.0.0.1:54323\n'
printf '  Logs:     %s\n' "$RUNTIME_DIR"
say "Nhấn Ctrl+C để dừng FastAPI và Vite (Supabase/Docker vẫn chạy)."

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$FRONTEND_URL"
fi

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 2
done

die "FastAPI hoặc Vite đã dừng ngoài dự kiến. Xem log trong $RUNTIME_DIR"
