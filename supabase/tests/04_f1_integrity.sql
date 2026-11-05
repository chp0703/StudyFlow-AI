-- Approved F1 persistence integrity, catalog and constraint behavior.
-- Run only against a disposable local Supabase database.
begin;
select no_plan();
set local search_path = public, extensions;

select ok((select c.relrowsecurity and c.relforcerowsecurity
 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='app_private' and c.relname='academic_tasks'),
 'academic tasks enable and force RLS');

-- Preserve original same-owner FK coverage and scope names to owning tables.
select ok(exists(select 1 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace
 where n.nspname='app_private' and t.relname=e.table_name
 and c.conname=e.constraint_name and c.contype='f' and cardinality(c.conkey)=2
 and (select a.attname from pg_attribute a where a.attrelid=c.conrelid
      and a.attnum=c.conkey[1])='user_id'
 and (select a.attname from pg_attribute a where a.attrelid=c.confrelid
      and a.attnum=c.confkey[1])='user_id'),e.description)
 from (values
 ('user_profiles','fk_profiles_current_plan_owner','current plan same-owner FK'),
 ('task_candidates','fk_candidates_confirmed_task_owner','confirmed candidate task same-owner FK'),
 ('academic_tasks','fk_tasks_candidate_owner','task candidate same-owner FK'),
 ('study_plans','fk_plans_previous_owner','previous plan same-owner FK'),
 ('study_plans','fk_plans_source_proposal_owner','source proposal same-owner FK'),
 ('plan_proposals','fk_proposals_base_plan_owner','base plan same-owner FK'),
 ('plan_proposals','fk_proposals_committed_plan_owner','committed plan same-owner FK'),
 ('study_blocks','fk_blocks_plan_owner','block plan same-owner FK'),
 ('study_blocks','fk_blocks_task_owner','block task same-owner FK'),
 ('pending_actions','fk_actions_candidate_owner','action candidate same-owner FK'),
 ('pending_actions','fk_actions_proposal_owner','action proposal same-owner FK'),
 ('pending_actions','fk_actions_dependency_owner','action dependency same-owner FK'),
 ('approval_actions','fk_approval_candidate_owner','approval candidate same-owner FK'),
 ('approval_actions','fk_approval_pending_owner','approval pending action same-owner FK'),
 ('approval_actions','fk_approval_proposal_owner','approval proposal same-owner FK'))
 e(table_name,constraint_name,description);
select ok(exists(select 1 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace where n.nspname='app_private'
 and t.relname='study_blocks' and c.conname='ex_study_blocks_plan_time' and c.contype='x'),
 'study block snapshot overlap exclusion');
select ok(exists(select 1 from pg_index i join pg_class idx on idx.oid=i.indexrelid
 join pg_class t on t.oid=i.indrelid join pg_namespace n on n.oid=t.relnamespace
 where n.nspname='app_private' and t.relname='pending_actions'
 and idx.relname='ix_pending_awaiting_conversation' and i.indpred is not null),
 'awaiting conversation actions have a partial lookup index');
select ok(exists(select 1 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace where n.nspname='app_private'
 and t.relname='idempotency_records' and c.conname='idempotency_expiry_check' and c.contype='c'),
 'domain idempotency has an expiry-order constraint');

-- Exact approved keys for domain entities and durable infrastructure.
select is((select array_agg(a.attname::text order by key.position)
 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace
 cross join lateral unnest(c.conkey) with ordinality key(attnum,position)
 join pg_attribute a on a.attrelid=t.oid and a.attnum=key.attnum
 where n.nspname='app_private' and t.relname=e.table_name and c.contype='p'),
 e.columns,e.table_name || ' uses the approved primary key')
 from (values
 ('user_profiles',array['user_id']),
 ('task_candidates',array['candidate_id']),
 ('academic_tasks',array['task_id']),
 ('time_windows',array['window_id']),
 ('study_plans',array['plan_id']),
 ('study_blocks',array['plan_id','block_id']),
 ('plan_proposals',array['proposal_id']),
 ('pending_actions',array['action_id']),
 ('approval_actions',array['approval_action_id']),
 ('idempotency_records',array['user_id','operation','idempotency_key']),
 ('conversation_records',array['user_id','conversation_id']),
 ('source_messages',array['message_id']),
 ('api_request_receipts',array['user_id','http_operation','idempotency_key']),
 ('action_presentations',array['user_id','action_id','action_version']),
 ('workflow_continuations',array['user_id','source_message_id']),
 ('rpc_attestation_keys',array['key_id'])) e(table_name,columns);

-- Durable versions must not truncate JSON-safe integers to int4.
select ok(exists(select 1 from pg_attribute a join pg_class t on t.oid=a.attrelid
 join pg_namespace n on n.oid=t.relnamespace
 where n.nspname='app_private' and t.relname=e.table_name and a.attname=e.column_name
 and not a.attisdropped and a.atttypid=e.type_name::regtype and a.attnotnull=e.not_null),
 e.table_name || '.' || e.column_name || ' has approved type and nullability')
 from (values
 ('api_request_receipts','lease_version','bigint',true),
 ('api_request_receipts','lease_until','timestamptz',false),
 ('api_request_receipts','response','jsonb',false),
 ('api_request_receipts','http_status','bigint',false),
 ('action_presentations','action_version','bigint',true),
 ('action_presentations','target_version','bigint',true),
 ('action_presentations','presentation','jsonb',true),
 ('workflow_continuations','version','bigint',true),
 ('workflow_continuations','cursor','bigint',true),
 ('workflow_continuations','extraction','jsonb',true),
 ('workflow_continuations','depends_on','jsonb',true),
 ('workflow_continuations','completed_steps','jsonb',true),
 ('workflow_continuations','awaiting_reference','jsonb',false),
 ('rpc_attestation_keys','key_id','text',true),
 ('rpc_attestation_keys','key_material','bytea',true),
 ('rpc_attestation_keys','not_before','timestamptz',true),
 ('rpc_attestation_keys','not_after','timestamptz',true))
 e(table_name,column_name,type_name,not_null);

-- Behavioral checks do not depend on implementer constraint names.
select throws_ok($q$insert into app_private.rpc_attestation_keys
 (key_id,key_material,not_before,not_after) values
 ('sol-short-key',decode('00','hex'),clock_timestamp(),clock_timestamp()+interval '1 hour')$q$,
 '23514',null,'key store rejects fewer than 32 key bytes');
select throws_ok($q$insert into app_private.rpc_attestation_keys
 (key_id,key_material,not_before,not_after) values
 ('sol-invalid-window',decode(repeat('01',32),'hex'),
 '2026-11-05T00:00:00Z','2026-11-05T00:00:00Z')$q$,
 '23514',null,'key validity end must be later than start');

select * from finish();
rollback;
