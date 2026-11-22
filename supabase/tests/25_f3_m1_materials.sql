begin;
set local search_path = public, extensions;
select plan(22);
select is((select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'app_private' and c.relname in
        ('learning_material_receipts','learning_session','learning_turn','session_outcome')
    and c.relrowsecurity and c.relforcerowsecurity), 4::bigint, 'New learning tables FORCE RLS');
select ok(not has_table_privilege('authenticated','app_private.learning_material_receipts','SELECT'), 'No direct receipt reads');
select ok(not has_table_privilege('authenticated','app_private.learning_session','SELECT'), 'No direct session reads');
select ok(not has_table_privilege('authenticated','app_private.learning_turn','INSERT'), 'No direct turn writes');
select ok(not has_table_privilege('authenticated','app_private.session_outcome','INSERT'), 'No direct outcome writes');
select ok(not has_table_privilege('sf_rpc_owner','app_private.session_outcome','INSERT'), 'No outcome write before M4');
select ok(not has_function_privilege('anon','app_api.get_learning_material(jsonb)','EXECUTE'), 'No anonymous RPC reads');
select ok(not has_function_privilege('anon','app_api.reserve_learning_material(jsonb)','EXECUTE'), 'No anonymous RPC writes');
select ok(to_regclass('app_private.material_chunks_learning_cosine') is not null, 'Learning cosine index installed');
select ok(to_regclass('app_private.material_chunks_search') is not null, 'Assessment full-text index preserved');
-- Copy table checks without its foreign keys so each case exercises the M1 constraint.
create temporary table learning_turn_check_cases (like app_private.learning_turn including constraints including defaults);
select lives_ok(
    format('insert into learning_turn_check_cases (user_id, session_id, ordinal, role, kind, hint_level, content, supported)
            values (gen_random_uuid(), gen_random_uuid(), 1, %L, %L, %L, ''Test turn'', %L)',
           role, kind, level, case when role = 'ASSISTANT' then true end),
    format('%s/%s accepts level %s', role, kind, coalesce(level::text, 'NULL')))
from (values ('USER', 'ASK', null), ('USER', 'HINT', null), ('ASSISTANT', 'ASK', null),
             ('ASSISTANT', 'HINT', 1), ('ASSISTANT', 'HINT', 2), ('ASSISTANT', 'HINT', 3)) t(role, kind, level);

select throws_ok(
    format('insert into learning_turn_check_cases (user_id, session_id, ordinal, role, kind, hint_level, content, supported)
            values (gen_random_uuid(), gen_random_uuid(), 1, %L, %L, %L, ''Test turn'', %L)',
           role, kind, level, case when role = 'ASSISTANT' then true end),
    '23514', null,
    format('%s/%s rejects level %s', role, kind, coalesce(level::text, 'NULL')))
from (values ('USER', 'ASK', 1), ('USER', 'HINT', 1), ('ASSISTANT', 'ASK', 1),
             ('ASSISTANT', 'HINT', null), ('ASSISTANT', 'HINT', 0), ('ASSISTANT', 'HINT', 4)) t(role, kind, level);
select * from finish();
rollback;
