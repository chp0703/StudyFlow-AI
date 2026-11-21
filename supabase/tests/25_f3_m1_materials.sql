begin;
set local search_path = public, extensions;
select plan(10);
select is((select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'app_private' and c.relname in
        ('learning_material_receipts','learning_session','learning_turn','session_outcome')
    and c.relrowsecurity and c.relforcerowsecurity), 4::bigint, 'New learning tables FORCE RLS');
select ok(not has_table_privilege('authenticated','app_private.learning_material_receipts','SELECT'), 'No direct receipt reads');
select ok(not has_table_privilege('authenticated','app_private.learning_session','SELECT'), 'No direct session reads');
select ok(not has_table_privilege('authenticated','app_private.learning_turn','INSERT'), 'No direct turn writes');
select ok(not has_table_privilege('authenticated','app_private.session_outcome','INSERT'), 'No direct outcome writes');
select ok(not has_table_privilege('sf_rpc_owner','app_private.session_outcome','UPDATE'), 'Outcomes are never updated (M4 inserts only via decision)');
select ok(not has_function_privilege('anon','app_api.get_learning_material(jsonb)','EXECUTE'), 'No anonymous RPC reads');
select ok(not has_function_privilege('anon','app_api.reserve_learning_material(jsonb)','EXECUTE'), 'No anonymous RPC writes');
select ok(to_regclass('app_private.material_chunks_learning_cosine') is not null, 'Learning cosine index installed');
select ok(to_regclass('app_private.material_chunks_search') is not null, 'Assessment full-text index preserved');
select * from finish();
rollback;
