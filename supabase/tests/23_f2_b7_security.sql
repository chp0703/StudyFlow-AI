begin;
select plan(23);
select has_table('app_private','revision_recommendations','B7 recommendations are durable');
select ok((select relrowsecurity and relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='app_private' and c.relname='revision_recommendations'),'B7 FORCE RLS enabled');
select ok(not has_table_privilege('authenticated','app_private.revision_recommendations','SELECT'),'B7 clients cannot read tables directly');
select ok(not has_table_privilege('authenticated','app_private.revision_recommendations','INSERT'),'B7 clients cannot inject recommendations');
select ok(not has_function_privilege('anon','app_api.create_revision_recommendation(jsonb)','EXECUTE'),'B7 creation denies anonymous callers');
select ok(not has_function_privilege('anon','app_api.decide_revision_recommendation(jsonb)','EXECUTE'),'B7 decisions deny anonymous callers');
select ok(has_function_privilege('authenticated','app_api.decide_revision_recommendation(jsonb)','EXECUTE'),'B7 authenticated callers can reach signed decision boundary');
select ok(not app_private.rpc_is_read('create_revision_recommendation'),'B7 creation requires write attestation');
select ok(not app_private.rpc_is_read('decide_revision_recommendation'),'B7 decisions require write attestation');
select is(app_private.canonical_json('{"error_rate":0.3333333333333333}'::jsonb), '{"error_rate":0.3333333333333333}', 'B7 fractional ratios remain signable without rounding the evidence to four places');
select col_has_check('app_private', 'revision_recommendations', 'suggested_minutes',
    'B7 storage constrains learner-selected minutes');
select col_has_check('app_private', 'revision_recommendations', 'priority',
    'B7 storage constrains learner-selected priority');

select ok(col_description(attrelid, attnum) like 'Learner-selected duration%',
    'B7 minutes document the source of the stored value')
from pg_attribute
where attrelid = 'app_private.revision_recommendations'::regclass and attname = 'suggested_minutes';

select ok(col_description(attrelid, attnum) like 'Learner-selected Planner priority%',
    'B7 priority documents the source of the stored value')
from pg_attribute
where attrelid = 'app_private.revision_recommendations'::regclass and attname = 'priority';

with request(args) as (
  values ('{"recommendation_id":"00000000-0000-4000-8000-000000000251",
            "pending_action_id":"00000000-0000-4000-8000-000000000261",
            "material_id":"00000000-0000-4000-8000-000000000201",
            "topic":"TCP","suggested_minutes":20,"priority":0.5}'::jsonb)
)
select is(app_private.matches_contract('CreateRevisionRecommendationArguments',
    (request.args - example.omit) || example.patch), example.valid, example.label)
from request cross join (values
  (array[]::text[], '{"suggested_minutes":15,"priority":0.1}'::jsonb, true, 'B7 lower boundary'),
  (array[]::text[], '{}'::jsonb, true, 'B7 accepts 20 minutes and priority 0.5'),
  (array[]::text[], '{"suggested_minutes":240,"priority":1}'::jsonb, true, 'B7 upper boundary'),
  (array['suggested_minutes'], '{}'::jsonb, false, 'B7 requires minutes'),
  (array['priority'], '{}'::jsonb, false, 'B7 requires priority'),
  (array[]::text[], '{"suggested_minutes":14}', false, 'B7 rejects minutes below 15'),
  (array[]::text[], '{"suggested_minutes":241}', false, 'B7 rejects minutes above 240'),
  (array[]::text[], '{"suggested_minutes":20.5}', false, 'B7 rejects fractional minutes'),
  (array[]::text[], '{"priority":0.7}', false, 'B7 rejects unsupported priority')
) as example(omit, patch, valid, label);

select * from finish();
rollback;
