# Runbook cho người tiếp nhận

## Môi trường mới

Python3.12+ thực, Git, Node20+ nếu cài CLI qua npm; Docker + SupabaseCLI3.0.0 cho DB local. Không dựa vào đường dẫn Python/venv/dependencies của người cũ.

```powershell
Set-Location E:\TDTT\StudyFlow-AI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-acceptance.txt
.\.venv\Scripts\python.exe -m pip install -r supabase\tests_concurrency\requirements.txt
```

Nếu `py` không có, dùng Python executable đã cài thật. Máy cũ có WindowsApps alias `python` không chạy được; reviewer dùng runtime bundled của Codex và PYTHONPATH ngoài repo. Những dependencies đó **không nằm trong ZIP**. Tránh commit `.venv` mới (có thể dùng venv ngoài repo hoặc thêm ignore local trước).

## Lệnh kiểm tra (tại repo root)

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -B contracts/check_contract.py
& $py -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_contract_addendum.py -v
& $py -B -m unittest discover -s backend/tests/acceptance_sol -v
& $py -B -m unittest discover -s backend/tests/unit -t . -v
& $py -B -m unittest discover -s tests -v
& $py -B backend/scripts/evaluate_planner.py
& $py -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_http_contract.py -v
```

Trạng thái mong đợi lúc nhận: WP0 checker/2cases fail; HTTP missing-factory setup error; scheduler xanh. `evidence/` trong ZIP là log tại lúc đóng gói, không tự cập nhật khi người nhận sửa source.

Factory đã freeze:

```python
backend.app.main.create_app(
    settings=None, *, rpc_transport=None, llm_transport=None,
    jwks_transport=None, clock=None,
) -> FastAPI
```

`backend.app.core.config.Settings`: supabase_url, supabase_publishable_key,
supabase_jwt_audience, supabase_jwt_algorithm, deepseek_api_key,
deepseek_base_url, deepseek_model, rpc_signing_key_id,
rpc_signing_secret_base64, cors_origins:list[str]. Transports HTTPX-compatible;
clock aware datetime. Xem WP3/API tests để giữ exact seam.

## DB thật, chỉ local dùng một lần

Chỉ chạy trên disposable Supabase local. Các lệnh reset dưới đây không dùng
`--remote`. CLI3.0.0 local là mặc định; đừng sao chép cờ CLI cũ từ docs cached.

```powershell
supabase --version
supabase start
supabase db reset --yes
supabase test db
```

SQL03–07 hiện có nhưng chưa đủ runtime để pass. Parse SQL không thực thi
PL/pgSQL/RLS/transactions. Sau khi DB code đủ, chạy concurrency:

```powershell
$env:F1_DB_TEST_DSN = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
& $py -B -m unittest discover -s supabase/tests_concurrency -v
Remove-Item Env:F1_DB_TEST_DSN
```

DSN này là local default, không phải mật khẩu cloud. Xác nhận `supabase status`
trước; harness từ chối remote/missing DSN và không skip giả. Authenticated SQL
sessions dùng trusted gateway claims để kiểm transaction/RLS; không chứng minh
JWT signature/HTTP thật. Lease test backdate đúng lease_until có ghi nhãn; chưa
chứng minh chờ wall-clock120s. Đọc README harness để thấy coverage thiếu.

CI hiện chạy local Supabase/pgTAP; **chưa thêm concurrency step và route upgrade**.
Khi thêm: install requirements, explicit DSN local, chạy harness sau migrations/
pgTAP; upgrade từ008 rồi migration up cần bằng chứng riêng. Không cho green vì
test bị skip/không discover/không chạy.

## Cấu hình live và các đầu vào còn thiếu

Copy `.env.example` sang `.env.local` và điền trên máy người có quyền. Không gửi
secret vào chat/ZIP/Git. Gemini không cần API key để phát triển; DeepSeek của
sản phẩm vẫn cần API key. Mẫu DEEPSEEK_MODEL đã chọn deepseek-flash theo docs tại
lúc làm; kiểm lại quyền model thực tế khi kết nối.

Supabase `phomrutsdhdgejlskwcb` mới chỉ xác minh public JWKS ES256. Cần biết
project chung hay demo, kiểm quyền/schema/migration history/dữ liệu; chạy
`supabase/scripts/inventory_demo.sql` bằng quyền hợp lệ. Chưa được reset cloud.
HMAC key là secret riêng backend–DB, không phải JWT secret/DeepSeek key; cần
provision kín sau khi schema qua CI. Có hai tài khoản demo tổng hợp để kiểm owner.

## Git và WIP

- Chưa merge main. Push integration đã được user cho phép; `git diff --check`
  trước commit. Commit tiếng Anh, scope nhỏ.
- ZIP `workspace/` là source snapshot tại lúc bàn giao, gồm files WIP chưa có
  trên GitHub. Đừng `reset --hard`, `clean -fd` hoặc overwrite bằng branch sạch.
- Bundle/patch trong ZIP không chứa `.git/config` hay login cache. Khôi phục theo
  README_KIT; sau restore phải kiểm `git status`, SHA và test thực tế.
- File `contracts/VALIDATION.md` do implementer viết chưa thể dùng thay reviewer
  logs; khi sửa xong phải cập nhật bằng chứng cho đúng.
