-- F2 B3 + B4: question draft generation, batch review presentation, UI verification, and listing.

alter table app_private.material_chunks
    add constraint material_chunks_owner_material_chunk_key unique (user_id, material_id, chunk_id);

alter table app_private.api_request_receipts
    drop constraint if exists api_request_receipts_http_operation_check;
alter table app_private.api_request_receipts
    add constraint api_request_receipts_http_operation_check
        check (http_operation in (
            'send_message', 'prepare_action', 'review_action', 'submit_decision', 'generate_question_drafts'
        ));

create table app_private.question_drafts (
    question_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    conversation_id uuid not null,
    material_id uuid not null,
    assessment_version text not null default '1.0.0' check (assessment_version = '1.0.0'),
    version bigint not null default 1 check (version between 1 and 9007199254740991),
    topic text not null check (length(btrim(topic)) between 1 and 120),
    question_type text not null check (question_type in ('MCQ', 'TRUE_FALSE')),
    stem text not null check (length(stem) between 1 and 2000 and stem ~ '\S'),
    options jsonb not null check (jsonb_typeof(options) = 'array' and jsonb_array_length(options) between 2 and 6),
    answer_key text not null check (length(btrim(answer_key)) between 1 and 32),
    explanation text check (explanation is null or (length(explanation) between 1 and 2000 and explanation ~ '\S')),
    source_chunk_ids jsonb not null check (
        jsonb_typeof(source_chunk_ids) = 'array' and jsonb_array_length(source_chunk_ids) between 1 and 10
    ),
    status text not null default 'DRAFT' check (status in ('DRAFT', 'VERIFIED', 'REJECTED')),
    model text check (model is null or (length(btrim(model)) between 1 and 100)),
    prompt_version text not null check (length(btrim(prompt_version)) between 1 and 64),
    verified_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, question_id),
    unique (user_id, material_id, question_id),
    foreign key (user_id, conversation_id) references app_private.conversation_records(user_id, conversation_id)
        on delete restrict on update restrict,
    foreign key (user_id, material_id) references app_private.materials(user_id, material_id)
        on delete restrict on update restrict,
    check ((status = 'VERIFIED') = (verified_at is not null))
);

create table app_private.question_draft_sources (
    question_id uuid not null,
    chunk_id uuid not null,
    user_id uuid not null,
    material_id uuid not null,
    source_order integer not null check (source_order between 0 and 9),
    created_at timestamptz not null default clock_timestamp(),
    primary key (question_id, chunk_id),
    unique (question_id, source_order),
    foreign key (user_id, material_id, question_id)
        references app_private.question_drafts(user_id, material_id, question_id)
        on delete restrict on update restrict,
    foreign key (user_id, material_id, chunk_id)
        references app_private.material_chunks(user_id, material_id, chunk_id)
        on delete restrict on update restrict
);

create table app_private.question_draft_batch_items (
    user_id uuid not null,
    action_id uuid not null,
    question_id uuid not null,
    item_order integer not null check (item_order between 0 and 9),
    created_at timestamptz not null default clock_timestamp(),
    primary key (user_id, action_id, question_id),
    unique (user_id, action_id, item_order),
    unique (user_id, question_id),
    foreign key (user_id, action_id) references app_private.pending_actions(user_id, action_id)
        on delete restrict on update restrict,
    foreign key (user_id, question_id) references app_private.question_drafts(user_id, question_id)
        on delete restrict on update restrict
);

create index ix_question_drafts_owner_created
    on app_private.question_drafts (user_id, created_at, question_id);
create index ix_question_drafts_owner_filters
    on app_private.question_drafts (user_id, status, material_id, topic, created_at, question_id);
create index ix_question_draft_sources_chunk
    on app_private.question_draft_sources (user_id, chunk_id);

alter table app_private.question_drafts enable row level security;
alter table app_private.question_drafts force row level security;
alter table app_private.question_draft_sources enable row level security;
alter table app_private.question_draft_sources force row level security;
alter table app_private.question_draft_batch_items enable row level security;
alter table app_private.question_draft_batch_items force row level security;

revoke all on app_private.question_drafts, app_private.question_draft_sources,
    app_private.question_draft_batch_items from public, anon, authenticated;
grant select, insert, update on app_private.question_drafts to sf_rpc_owner;
grant select, insert on app_private.question_draft_sources, app_private.question_draft_batch_items to sf_rpc_owner;

create policy question_drafts_select on app_private.question_drafts
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy question_drafts_insert on app_private.question_drafts
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy question_drafts_update on app_private.question_drafts
    for update to sf_rpc_owner using (user_id = app_private.current_uid())
    with check (user_id = app_private.current_uid());

create policy question_draft_sources_select on app_private.question_draft_sources
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy question_draft_sources_insert on app_private.question_draft_sources
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());

create policy question_draft_batch_items_select on app_private.question_draft_batch_items
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy question_draft_batch_items_insert on app_private.question_draft_batch_items
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());

-- VERIFIED/REJECTED questions are immutable; DRAFT content is immutable (only terminal decision transitions status/version).
create function app_private.guard_question_draft() returns trigger
language plpgsql set search_path = '' as $$
declare
    v_opt_ids text[];
    v_distinct_opts int;
    v_opt_count int;
begin
    if tg_op = 'DELETE' then
        raise exception 'question_drafts cannot be deleted' using errcode = '23514';
    end if;
    if tg_op = 'INSERT' then
        if new.status <> 'DRAFT' or new.version <> 1 or new.verified_at is not null then
            raise exception 'new question_draft must start in DRAFT at version 1 without verified_at' using errcode = '23514';
        end if;
    elsif tg_op = 'UPDATE' then
        if old.status in ('VERIFIED', 'REJECTED') then
            raise exception 'finalized question_draft is immutable' using errcode = '23514';
        end if;
        if new.status not in ('VERIFIED', 'REJECTED') or new.version <> old.version + 1 then
            raise exception 'question_draft update must finalize status and increment version' using errcode = '23514';
        end if;
        if (new.question_id, new.user_id, new.conversation_id, new.material_id, new.assessment_version,
            new.topic, new.question_type, new.stem, new.options, new.answer_key, new.explanation,
            new.source_chunk_ids, new.model, new.prompt_version, new.created_at)
           is distinct from
           (old.question_id, old.user_id, old.conversation_id, old.material_id, old.assessment_version,
            old.topic, old.question_type, old.stem, old.options, old.answer_key, old.explanation,
            old.source_chunk_ids, old.model, old.prompt_version, old.created_at) then
            raise exception 'question_draft content is immutable' using errcode = '23514';
        end if;
        new.updated_at := clock_timestamp();
    end if;

    select array_agg(o ->> 'option_id' order by ord), count(distinct o ->> 'option_id'), count(*)
    into v_opt_ids, v_distinct_opts, v_opt_count
    from jsonb_array_elements(new.options) with ordinality as x(o, ord);

    if v_opt_count is null or v_opt_count not between 2 and 6 or v_distinct_opts <> v_opt_count then
        raise exception 'question options must have 2-6 unique option_ids' using errcode = '23514';
    end if;
    if not (new.answer_key = any(v_opt_ids)) then
        raise exception 'answer_key must match one option_id' using errcode = '23514';
    end if;
    if new.question_type = 'TRUE_FALSE'
       and (v_opt_count <> 2 or not (v_opt_ids @> array['TRUE', 'FALSE'] and array['TRUE', 'FALSE'] @> v_opt_ids)) then
        raise exception 'TRUE_FALSE question must have exact option_ids TRUE and FALSE' using errcode = '23514';
    end if;
    return new;
end $$;

create function app_private.guard_question_draft_links() returns trigger
language plpgsql set search_path = '' as $$
begin
    raise exception 'question draft links are immutable' using errcode = '23514';
end $$;

create trigger trg_question_draft_guard
    before insert or update or delete on app_private.question_drafts
    for each row execute function app_private.guard_question_draft();
create trigger trg_question_draft_sources_immutable
    before update or delete on app_private.question_draft_sources
    for each row execute function app_private.guard_question_draft_links();
create trigger trg_question_draft_batch_items_immutable
    before update or delete on app_private.question_draft_batch_items
    for each row execute function app_private.guard_question_draft_links();

create function app_private.question_json(r app_private.question_drafts) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'assessment_version', r.assessment_version,
        'question_id', r.question_id,
        'user_id', r.user_id,
        'conversation_id', r.conversation_id,
        'material_id', r.material_id,
        'version', r.version,
        'topic', r.topic,
        'question_type', r.question_type,
        'stem', r.stem,
        'options', r.options,
        'answer_key', r.answer_key,
        'explanation', r.explanation,
        'source_chunk_ids', r.source_chunk_ids,
        'status', r.status,
        'model', r.model,
        'prompt_version', r.prompt_version,
        'verified_at', case when r.verified_at is null then null else app_private.iso(r.verified_at) end,
        'created_at', app_private.iso(r.created_at),
        'updated_at', app_private.iso(r.updated_at)
    )
$$;

create function app_private.question_batch_source_chunks(p_uid uuid, p_action_id uuid) returns jsonb
language sql stable set search_path = '' as $$
    select coalesce(jsonb_agg(app_private.material_chunk_json(x) order by x.page, x.chunk_index, x.chunk_id), '[]'::jsonb)
    from (
        select distinct c.chunk_id, c.material_id, c.user_id, c.page, c.topic, c.chunk_index, c.text, c.search_vector, c.created_at
        from app_private.question_draft_batch_items bi
        join app_private.question_draft_sources qds
          on qds.user_id = bi.user_id and qds.question_id = bi.question_id
        join app_private.material_chunks c
          on c.user_id = qds.user_id and c.material_id = qds.material_id and c.chunk_id = qds.chunk_id
        where bi.user_id = p_uid and bi.action_id = p_action_id
    ) x
$$;

-- Include F2 question_drafts in the presentation digest only when present so existing F1 digests do not change.
create or replace function app_private.presentation_digest(p_action app_private.pending_actions, p_target_type text,
                                                           p_target_id uuid, p_target_version bigint,
                                                           p_presentation jsonb) returns text
language sql immutable set search_path = '' as $$
    select encode(extensions.digest(convert_to(app_private.canonical_json(
        jsonb_build_object(
            'intent', p_action.intent, 'state', p_action.state, 'draft_arguments', p_action.draft_arguments,
            'missing_fields', p_action.missing_fields, 'ambiguities', p_action.ambiguities,
            'target_type', p_target_type, 'target_id', p_target_id, 'target_version', p_target_version,
            'candidate_slots', p_presentation #> '{candidate,slots}', 'proposal', p_presentation -> 'proposal',
            'normalized_command', p_presentation -> 'normalized_command',
            'effective_policy', p_presentation -> 'effective_policy'
        ) || case when p_presentation ? 'question_drafts'
                  then jsonb_build_object('question_drafts', p_presentation -> 'question_drafts')
                  else '{}'::jsonb end
    ), 'UTF8'), 'sha256'), 'hex')
$$;

create or replace function app_private.store_presentation(p_request jsonb, p_uid uuid, p_action app_private.pending_actions,
                                                           p_presentation jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    c app_private.task_candidates;
    v_type text;
    v_target uuid;
    v_target_version bigint;
    v_message uuid := (p_request #>> '{execution_context,trusted_context,message_id}')::uuid;
    v_stored jsonb;
    v_db_items jsonb;
    v_db_sources jsonb;
    v_non_draft int;
begin
    if p_action.candidate_id is not null then
        select * into c from app_private.task_candidates where user_id = p_uid and candidate_id = p_action.candidate_id;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The candidate was not found.');
        end if;
        if p_presentation -> 'candidate' is null or p_presentation -> 'candidate' = 'null'::jsonb
           or c.status <> 'DRAFT'
           or (c.version, c.slots) is distinct from ((p_presentation #>> '{candidate,version}')::bigint, p_presentation #> '{candidate,slots}') then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The presented candidate no longer matches the draft.');
        end if;
        v_type := 'TASK_CANDIDATE'; v_target := c.candidate_id; v_target_version := c.version;
    elsif p_action.proposal_id is not null then
        select p.version into v_target_version from app_private.plan_proposals p
        where p.user_id = p_uid and p.proposal_id = p_action.proposal_id and p.status = 'PROPOSED';
        if v_target_version is null then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found or is no longer pending.');
        end if;
        v_type := 'PLAN_PROPOSAL'; v_target := p_action.proposal_id;
    elsif p_action.intent = 'VERIFY_QUESTION_DRAFTS' then
        select coalesce(jsonb_agg(app_private.question_json(q) order by bi.item_order), '[]'::jsonb),
               count(*) filter (where q.status <> 'DRAFT')
        into v_db_items, v_non_draft
        from app_private.question_draft_batch_items bi
        join app_private.question_drafts q on q.user_id = bi.user_id and q.question_id = bi.question_id
        where bi.user_id = p_uid and bi.action_id = p_action.action_id;
        v_db_sources := app_private.question_batch_source_chunks(p_uid, p_action.action_id);
        if jsonb_array_length(v_db_items) = 0 or jsonb_array_length(v_db_sources) = 0 or coalesce(v_non_draft, 0) > 0
           or (p_presentation #> '{question_drafts,items}') is distinct from v_db_items
           or (p_presentation #> '{question_drafts,source_chunks}') is distinct from v_db_sources then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The presented question drafts no longer match the stored batch.');
        end if;
        v_type := 'PENDING_ACTION'; v_target := p_action.action_id; v_target_version := p_action.version;
    else
        v_type := 'PENDING_ACTION'; v_target := p_action.action_id; v_target_version := p_action.version;
    end if;
    v_stored := jsonb_set(p_presentation, '{pending_action}', app_private.pending_json(p_action));
    insert into app_private.action_presentations
        (user_id, action_id, action_version, target_type, target_id, target_version, content_digest, presentation,
         source_message_id)
    values (p_uid, p_action.action_id, p_action.version, v_type, v_target, v_target_version,
            app_private.presentation_digest(p_action, v_type, v_target, v_target_version, v_stored), v_stored,
            case when exists (select 1 from app_private.source_messages m where m.user_id = p_uid and m.message_id = v_message)
                 then v_message end);
    return null;
end $$;

-- Allocate stable action_id on receipt claim for generate_question_drafts too.
create or replace function app_api.claim_api_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'claim_api_receipt', 'ClaimApiReceiptArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_now timestamptz := clock_timestamp();
    r app_private.api_request_receipts;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if p_request #>> '{execution_context,conversation_id}' is distinct from v_args ->> 'conversation_id' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The conversation does not match the request context.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into r from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_args ->> 'http_operation'
          and idempotency_key = v_args ->> 'idempotency_key';
        if not found then
            insert into app_private.api_request_receipts
                (user_id, http_operation, idempotency_key, request_fingerprint, state, lease_version,
                 lease_until, message_id, action_id)
            values (v_uid, v_args ->> 'http_operation', v_args ->> 'idempotency_key',
                    v_args ->> 'request_fingerprint', 'IN_PROGRESS', 1, v_now + interval '120 seconds',
                    extensions.gen_random_uuid(),
                    case when v_args ->> 'http_operation' in ('send_message', 'prepare_action', 'generate_question_drafts')
                         then extensions.gen_random_uuid() end)
            returning * into r;
        elsif r.request_fingerprint <> v_args ->> 'request_fingerprint' then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT',
                'The idempotency key was already used with a different request.');
        elsif r.state = 'IN_PROGRESS' then
            if r.lease_until > v_now then
                return app_private.error_result(p_request, 'SERVICE_UNAVAILABLE',
                    'The same request is still being processed.', true);
            end if;
            update app_private.api_request_receipts
            set lease_version = lease_version + 1, lease_until = v_now + interval '120 seconds'
            where user_id = r.user_id and http_operation = r.http_operation and idempotency_key = r.idempotency_key
            returning * into r;
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.receipt_json(r));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'get_scheduling_context', 'lookup_operation_result',
        'list_time_windows', 'get_workflow_context', 'get_workflow_continuation',
        'get_ingestion_source', 'get_assessment_material', 'search_material_chunks', 'list_questions'
    )
$$;

-- Atomically stores generated DRAFT questions, chunk source links, VERIFY_QUESTION_DRAFTS pending_action,
-- batch item links, and ActionPresentation; returns QuestionDraftBatchResult (DRAFTED).
create or replace function app_api.create_question_drafts(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'create_question_drafts', 'CreateQuestionDraftsArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_args jsonb := p_request -> 'arguments';
    v_material_id uuid;
    v_action_id uuid;
    v_fp_input jsonb;
    v_fp text;
    v_reply jsonb;
    v_material app_private.materials;
    v_draft jsonb;
    v_opt_ids text[];
    v_distinct_opts int;
    v_opt_count int;
    v_chunk_count int;
    v_qid uuid;
    v_chunk_id uuid;
    v_idx int;
    v_src_idx int;
    v_qids jsonb := '[]'::jsonb;
    v_items jsonb := '[]'::jsonb;
    v_source_chunks jsonb := '[]'::jsonb;
    v_action app_private.pending_actions;
    v_pres jsonb;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and conversation are required.');
    end if;
    if v_args ->> 'conversation_id' is distinct from v_conv::text then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Conversation does not match execution_context.');
    end if;
    v_material_id := (v_args ->> 'material_id')::uuid;
    if v_args ? 'generation_params' then
        v_fp_input := jsonb_build_object(
            'conversation_id', v_args -> 'conversation_id',
            'material_id', v_args -> 'material_id',
            'generation_params', v_args -> 'generation_params'
        );
    else
        v_fp_input := v_args;
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, 'create_question_drafts', v_fp_input);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        select * into v_material from app_private.materials
        where material_id = v_material_id and user_id = v_uid and conversation_id = v_conv and status = 'READY';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
        end if;

        if exists (
            select 1 from app_private.pending_actions x
            where x.user_id = v_uid and x.conversation_id = v_conv
              and x.state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL')
        ) then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED',
                'The conversation already has an awaiting action; review or cancel it first.');
        end if;

        -- Validate all draft invariants before writing any rows.
        for v_draft in select value from jsonb_array_elements(v_args -> 'drafts') loop
            if v_draft ->> 'user_id' is distinct from v_uid::text
               or v_draft ->> 'conversation_id' is distinct from v_conv::text
               or v_draft ->> 'material_id' is distinct from v_material_id::text
               or v_draft ->> 'status' is distinct from 'DRAFT'
               or (v_draft ->> 'version')::bigint is distinct from 1
               or (v_draft -> 'verified_at') is distinct from 'null'::jsonb then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Draft metadata must match owner, conversation, material, and initial DRAFT state.');
            end if;
            if not (v_material.topics ? (v_draft ->> 'topic')) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Draft topic does not belong to the material.');
            end if;

            select array_agg(o ->> 'option_id' order by ord), count(distinct o ->> 'option_id'), count(*)
            into v_opt_ids, v_distinct_opts, v_opt_count
            from jsonb_array_elements(v_draft -> 'options') with ordinality as x(o, ord);
            if v_opt_count is null or v_opt_count not between 2 and 6 or v_distinct_opts <> v_opt_count then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Question options must have 2 to 6 unique option_ids.');
            end if;
            if not ((v_draft ->> 'answer_key') = any(v_opt_ids)) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'answer_key must match one of the question options.');
            end if;
            if v_draft ->> 'question_type' = 'TRUE_FALSE'
               and (v_opt_count <> 2 or not (v_opt_ids @> array['TRUE', 'FALSE'] and array['TRUE', 'FALSE'] @> v_opt_ids)) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'TRUE_FALSE question must have exact option_ids TRUE and FALSE.');
            end if;

            select count(distinct c.chunk_id) into v_chunk_count
            from jsonb_array_elements_text(v_draft -> 'source_chunk_ids') s(cid)
            join app_private.material_chunks c
              on c.user_id = v_uid and c.material_id = v_material_id
             and c.chunk_id = s.cid::uuid and c.topic = v_draft ->> 'topic';
            if v_chunk_count <> jsonb_array_length(v_draft -> 'source_chunk_ids') then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Question source_chunk_ids must reference chunks of the target material and topic.');
            end if;
        end loop;

        v_action_id := coalesce((v_args ->> 'action_id')::uuid, extensions.gen_random_uuid());
        if exists (select 1 from app_private.pending_actions where user_id = v_uid and action_id = v_action_id) then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action already exists.');
        end if;

        for v_draft, v_idx in select value, ordinality - 1 from jsonb_array_elements(v_args -> 'drafts') with ordinality loop
            v_qid := (v_draft ->> 'question_id')::uuid;
            insert into app_private.question_drafts (
                question_id, user_id, conversation_id, material_id, assessment_version, version, topic,
                question_type, stem, options, answer_key, explanation, source_chunk_ids, status, model,
                prompt_version, verified_at
            ) values (
                v_qid, v_uid, v_conv, v_material_id, '1.0.0', 1, v_draft ->> 'topic',
                v_draft ->> 'question_type', v_draft ->> 'stem', v_draft -> 'options', v_draft ->> 'answer_key',
                v_draft ->> 'explanation', v_draft -> 'source_chunk_ids', 'DRAFT', v_draft ->> 'model',
                v_draft ->> 'prompt_version', null
            );
            for v_chunk_id, v_src_idx in
                select value::uuid, ordinality - 1 from jsonb_array_elements_text(v_draft -> 'source_chunk_ids') with ordinality
            loop
                insert into app_private.question_draft_sources (question_id, chunk_id, user_id, material_id, source_order)
                values (v_qid, v_chunk_id, v_uid, v_material_id, v_src_idx);
            end loop;
            v_qids := v_qids || jsonb_build_array(v_qid);
        end loop;

        insert into app_private.pending_actions (
            action_id, user_id, conversation_id, version, intent, state, requires_review, candidate_id,
            proposal_id, draft_arguments, missing_fields, ambiguities, depends_on_action_id
        ) values (
            v_action_id, v_uid, v_conv, 1, 'VERIFY_QUESTION_DRAFTS', 'AWAITING_APPROVAL', false, null,
            null, jsonb_build_object('material_id', v_material_id, 'question_ids', v_qids),
            '[]'::jsonb, '[]'::jsonb, null
        ) returning * into v_action;

        for v_qid, v_idx in select value::uuid, ordinality - 1 from jsonb_array_elements_text(v_qids) with ordinality loop
            insert into app_private.question_draft_batch_items (user_id, action_id, question_id, item_order)
            values (v_uid, v_action.action_id, v_qid, v_idx);
        end loop;

        select coalesce(jsonb_agg(app_private.question_json(q) order by bi.item_order), '[]'::jsonb)
        into v_items
        from app_private.question_draft_batch_items bi
        join app_private.question_drafts q on q.user_id = bi.user_id and q.question_id = bi.question_id
        where bi.user_id = v_uid and bi.action_id = v_action.action_id;

        v_source_chunks := app_private.question_batch_source_chunks(v_uid, v_action.action_id);
        v_pres := jsonb_build_object(
            'kind', 'ACTION_PRESENTATION',
            'pending_action', app_private.pending_json(v_action),
            'candidate', null,
            'proposal', null,
            'normalized_command', null,
            'effective_policy', null,
            'schedule_confirmation', null,
            'question_drafts', jsonb_build_object('items', v_items, 'source_chunks', v_source_chunks)
        );
        v_error := app_private.store_presentation(p_request, v_uid, v_action, v_pres);
        if v_error is not null then
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;

        v_result := app_private.ok_result(p_request, 'DRAFTED', jsonb_build_object('items', v_items, 'source_chunks', v_source_chunks));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'create_question_drafts', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'Unable to store question drafts batch.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- UI-only approval/rejection guard and atomic batch transition for VERIFY_QUESTION_DRAFTS.
create or replace function app_api.verify_question_drafts(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'verify_question_drafts', 'VerifyQuestionDraftsArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_decision text := v_args ->> 'decision';
    v_action_id uuid := (v_args ->> 'action_id')::uuid;
    v_expected bigint := (v_args ->> 'expected_action_version')::bigint;
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    v_action app_private.pending_actions;
    v_pres app_private.action_presentations;
    v_batch_ids uuid[];
    v_arg_ids uuid[];
    v_db_items jsonb;
    v_db_sources jsonb;
    v_non_draft int;
    v_now timestamptz := clock_timestamp();
    v_items jsonb;
    v_outcome text;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null or v_args ->> 'conversation_id' is distinct from v_conv::text then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and matching conversation are required.');
    end if;
    if jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or v_approval ->> 'source' <> 'UI' or (v_approval -> 'source_message_id') is distinct from 'null'::jsonb
       or v_approval ->> 'user_id' is distinct from v_uid::text
       or v_approval ->> 'decision' is distinct from v_decision
       or v_approval ->> 'target_type' <> 'PENDING_ACTION'
       or v_approval ->> 'target_id' is distinct from v_action_id::text
       or (v_approval ->> 'target_version')::bigint is distinct from v_expected
       or v_ref ->> 'target_type' <> 'PENDING_ACTION'
       or v_ref ->> 'action_id' is distinct from v_action_id::text
       or (v_ref ->> 'action_version')::bigint is distinct from v_expected
       or v_ref ->> 'target_id' is distinct from v_action_id::text
       or (v_ref ->> 'target_version')::bigint is distinct from v_expected then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED',
            'Question verification requires an explicit UI approval reference for this exact pending action version.');
    end if;

    v_binding := jsonb_build_object(
        'decision', v_decision, 'action_id', v_ref -> 'action_id', 'action_version', v_ref -> 'action_version',
        'target_type', 'PENDING_ACTION', 'target_id', v_ref -> 'target_id', 'target_version', v_ref -> 'target_version'
    );
    v_fp := app_private.domain_fingerprint(v_uid, 'verify_question_drafts', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'verify_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'verify_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        select * into v_action from app_private.pending_actions
        where user_id = v_uid and action_id = v_action_id and conversation_id = v_conv
          and intent = 'VERIFY_QUESTION_DRAFTS' for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The pending verification action was not found.');
        end if;
        if v_action.requires_review then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'The action must be reviewed before it can be decided.');
        end if;
        if v_action.version <> v_expected or v_action.state <> 'AWAITING_APPROVAL' then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The pending action changed since it was presented.');
        end if;

        select * into v_pres from app_private.action_presentations
        where user_id = v_uid and action_id = v_action.action_id and action_version = v_action.version;
        if not found or v_pres.target_type <> 'PENDING_ACTION' or v_pres.target_id <> v_action.action_id
           or v_pres.target_version <> v_action.version
           or v_pres.content_digest <> app_private.presentation_digest(
               v_action, 'PENDING_ACTION', v_action.action_id, v_action.version, v_pres.presentation) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The question batch was not presented by the server.');
        end if;

        perform 1 from app_private.question_drafts q
        join app_private.question_draft_batch_items bi on bi.user_id = q.user_id and bi.question_id = q.question_id
        where bi.user_id = v_uid and bi.action_id = v_action.action_id
        order by bi.item_order for update of q;

        select array_agg(bi.question_id order by bi.item_order),
               coalesce(jsonb_agg(app_private.question_json(q) order by bi.item_order), '[]'::jsonb),
               count(*) filter (where q.status <> 'DRAFT')
        into v_batch_ids, v_db_items, v_non_draft
        from app_private.question_draft_batch_items bi
        join app_private.question_drafts q on q.user_id = bi.user_id and q.question_id = bi.question_id
        where bi.user_id = v_uid and bi.action_id = v_action.action_id;

        select array_agg(x::uuid order by ord) into v_arg_ids
        from jsonb_array_elements_text(v_args -> 'question_ids') with ordinality as t(x, ord);

        if v_batch_ids is null or cardinality(v_batch_ids) = 0 or coalesce(v_non_draft, 0) > 0 then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'One or more questions are no longer in DRAFT.');
        end if;
        if (select array_agg(u order by u) from unnest(v_batch_ids) u)
           is distinct from (select array_agg(u order by u) from unnest(v_arg_ids) u) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'question_ids must match the presented batch.');
        end if;
        v_db_sources := app_private.question_batch_source_chunks(v_uid, v_action.action_id);
        if (v_pres.presentation #> '{question_drafts,items}') is distinct from v_db_items
           or (v_pres.presentation #> '{question_drafts,source_chunks}') is distinct from v_db_sources then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The stored questions no longer match the presented snapshot.');
        end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             pending_action_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'PENDING_ACTION', v_action.action_id, v_action.version,
                v_decision, 'UI', null, v_action.action_id);

        update app_private.question_drafts
        set status = case when v_decision = 'APPROVE' then 'VERIFIED' else 'REJECTED' end,
            version = version + 1,
            verified_at = case when v_decision = 'APPROVE' then v_now else null end
        where user_id = v_uid and question_id = any(v_batch_ids);

        update app_private.pending_actions
        set state = case when v_decision = 'APPROVE' then 'COMPLETED' else 'CANCELLED' end,
            version = version + 1
        where user_id = v_uid and action_id = v_action.action_id;

        select coalesce(jsonb_agg(app_private.question_json(q) order by bi.item_order), '[]'::jsonb)
        into v_items
        from app_private.question_draft_batch_items bi
        join app_private.question_drafts q on q.user_id = bi.user_id and q.question_id = bi.question_id
        where bi.user_id = v_uid and bi.action_id = v_action.action_id;

        v_outcome := case when v_decision = 'APPROVE' then 'COMMITTED' else 'REJECTED' end;
        v_result := app_private.ok_result(p_request, v_outcome, jsonb_build_object('items', v_items, 'source_chunks', v_db_sources));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'verify_question_drafts', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The verification target is no longer valid.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- Read-only keyset paginated listing of owner questions filtered by material_id, topic, and status.
create or replace function app_api.list_questions(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'list_questions', 'ListQuestionsArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_material_id uuid := (v_args ->> 'material_id')::uuid;
    v_topic text := v_args ->> 'topic';
    v_status text := v_args ->> 'status';
    v_size int := (v_args ->> 'page_size')::int;
    v_filter jsonb;
    v_pos jsonb;
    v_items jsonb;
    v_more boolean;
    v_last_at text;
    v_last_id text;
    v_next text;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        v_filter := jsonb_build_object('m', v_material_id, 't', v_topic, 's', v_status);
        if v_args ->> 'cursor' is not null then
            v_pos := app_private.cursor_decode(v_uid, v_filter, v_args ->> 'cursor');
        end if;
        with page as (
            select q, row_number() over (order by q.created_at, q.question_id) as rn
            from app_private.question_drafts q
            where q.user_id = v_uid
              and (v_material_id is null or q.material_id = v_material_id)
              and (v_topic is null or q.topic = v_topic)
              and (v_status is null or q.status = v_status)
              and (v_pos is null or (q.created_at, q.question_id) > ((v_pos ->> 0)::timestamptz, (v_pos ->> 1)::uuid))
            order by q.created_at, q.question_id
            limit v_size + 1
        )
        select coalesce(jsonb_agg(app_private.question_json(p.q) order by p.rn) filter (where p.rn <= v_size), '[]'::jsonb),
               max(p.rn) > v_size,
               max(app_private.iso((p.q).created_at)) filter (where p.rn = v_size),
               max(((p.q).question_id)::text) filter (where p.rn = v_size)
        into v_items, v_more, v_last_at, v_last_id from page p;
        if v_more then
            v_next := app_private.cursor_encode(v_uid, v_filter, jsonb_build_array(v_last_at, v_last_id));
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('items', v_items, 'next_cursor', v_next));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.guard_question_draft() owner to sf_rpc_owner;
alter function app_private.guard_question_draft_links() owner to sf_rpc_owner;
alter function app_private.question_json(app_private.question_drafts) owner to sf_rpc_owner;
alter function app_private.question_batch_source_chunks(uuid, uuid) owner to sf_rpc_owner;
alter function app_private.presentation_digest(app_private.pending_actions, text, uuid, bigint, jsonb) owner to sf_rpc_owner;
alter function app_private.store_presentation(jsonb, uuid, app_private.pending_actions, jsonb) owner to sf_rpc_owner;
alter function app_private.rpc_is_read(text) owner to sf_rpc_owner;

revoke all on function app_private.guard_question_draft(),
    app_private.guard_question_draft_links(),
    app_private.question_json(app_private.question_drafts),
    app_private.question_batch_source_chunks(uuid, uuid),
    app_private.presentation_digest(app_private.pending_actions, text, uuid, bigint, jsonb),
    app_private.store_presentation(jsonb, uuid, app_private.pending_actions, jsonb),
    app_private.rpc_is_read(text) from public, anon, authenticated;

do $$
declare name text;
begin
    foreach name in array array['create_question_drafts', 'verify_question_drafts', 'list_questions'] loop
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', name);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', name);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', name);
    end loop;
end $$;
