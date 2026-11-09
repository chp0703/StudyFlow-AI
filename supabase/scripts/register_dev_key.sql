-- LOCAL DEVELOPMENT ONLY. Registers the HMAC key the backend signs RPC requests with.
-- Run it against the local database (never a cloud project), with your own random secret:
--   psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
--        -v key_id=f1-dev-1 -v secret_hex="$(openssl rand -hex 32)" -f supabase/scripts/register_dev_key.sql
-- Give the backend the same secret as RPC_SIGNING_SECRET_BASE64 (base64 of the same 32 bytes) and the same key id.
insert into app_private.rpc_attestation_keys (key_id, key_material, not_before, not_after)
values (:'key_id', decode(:'secret_hex', 'hex'), now() - interval '1 hour', now() + interval '30 days');
