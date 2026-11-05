-- Read-only preflight for an existing/shared project. Never reset cloud data.
-- Run as an authorized database administrator, before considering deployment.
-- This reports metadata only: no auth users, message text, keys or business rows.

select current_database() as database_name,
       current_user as database_role,
       current_setting('server_version') as postgres_version;

select extname, extversion
from pg_catalog.pg_extension
where extname in ('pgcrypto', 'btree_gist', 'pg_jsonschema', 'pgtap')
order by extname;

select n.nspname as schema_name, c.relname as table_name,
       c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced
from pg_catalog.pg_class c
join pg_catalog.pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('app_private', 'app_api', 'supabase_migrations')
  and c.relkind in ('r', 'p')
order by n.nspname, c.relname;

select n.nspname as schema_name, p.proname as routine_name,
       pg_catalog.pg_get_function_identity_arguments(p.oid) as arguments,
       p.prosecdef as security_definer,
       pg_catalog.pg_get_userbyid(p.proowner) as owner_role
from pg_catalog.pg_proc p
join pg_catalog.pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'app_api'
order by p.proname, arguments;

select rolname, rolcanlogin, rolsuper, rolbypassrls
from pg_catalog.pg_roles
where rolname = 'sf_rpc_owner';

select pg_catalog.to_regclass('supabase_migrations.schema_migrations')
       as migration_history_table;

-- Only if the previous result is non-null, run separately:
-- select version, name from supabase_migrations.schema_migrations order by version;
