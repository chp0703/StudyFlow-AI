-- Assessment keeps its current projection and evidence while F3 attaches an index.
grant delete on app_private.materials to sf_rpc_owner;
grant update, delete on app_private.material_chunks to sf_rpc_owner;
create policy learning_material_delete on app_private.materials for delete to sf_rpc_owner
    using (user_id = app_private.current_uid() and learning_status is not null);
create policy learning_chunks_delete on app_private.material_chunks for delete to sf_rpc_owner
    using (user_id = app_private.current_uid());
create policy learning_chunks_update on app_private.material_chunks for update to sf_rpc_owner
    using (user_id = app_private.current_uid()) with check (user_id = app_private.current_uid());

create or replace function app_private.guard_material_content() returns trigger
language plpgsql set search_path = '' as $$
declare material app_private.materials;
begin
    if tg_table_name = 'materials' then
        if tg_op = 'DELETE' and current_user = 'sf_rpc_owner' and old.learning_status is not null then
            return old;
        end if;
        if old.status = 'READY' then
            if tg_op = 'UPDATE' and current_user = 'sf_rpc_owner'
               and (to_jsonb(old) - array['learning_status','learning_error','course_label','learning_claim','learning_deadline'])
                 = (to_jsonb(new) - array['learning_status','learning_error','course_label','learning_claim','learning_deadline']) then
                return new;
            end if;
            raise exception 'READY material is immutable' using errcode = '23514';
        end if;
        if tg_op = 'UPDATE' and new.status = 'READY' and not exists (
            select 1 from app_private.material_chunks c
            where c.material_id = new.material_id and c.user_id = new.user_id and c.profile = 'assessment'
        ) then
            raise exception 'READY material needs chunks' using errcode = '23514';
        end if;
        if tg_op = 'DELETE' then return old; end if;
        return new;
    end if;

    if tg_op = 'DELETE' then
        if current_user = 'sf_rpc_owner' and exists (
            select 1 from app_private.materials m
            where m.material_id = old.material_id and m.user_id = old.user_id and m.learning_status is not null
        ) then
            return old;
        end if;
        raise exception 'Chunks are immutable' using errcode = '23514';
    end if;

    select * into material from app_private.materials m
    where m.material_id = new.material_id and m.user_id = new.user_id;
    if tg_op = 'UPDATE' then
        if current_user = 'sf_rpc_owner' and material.learning_status = 'INDEXING'
           and old.profile = 'assessment' and old.learning_ordinal is null and new.learning_ordinal is not null
           and (to_jsonb(old) - array['embedding','embedding_model','learning_ordinal','search_vector'])
             = (to_jsonb(new) - array['embedding','embedding_model','learning_ordinal','search_vector']) then
            return new;
        end if;
        raise exception 'Chunks are immutable' using errcode = '23514';
    end if;
    if material.material_id is null or new.page > material.page_count or not (material.topics ? new.topic)
       or (new.profile = 'assessment' and material.status <> 'UPLOADED')
       or (new.profile = 'learning' and material.learning_status is distinct from 'INDEXING') then
        raise exception 'Chunk provenance mismatch' using errcode = '23514';
    end if;
    return new;
end
$$;

create or replace function app_private.question_batch_source_chunks(p_uid uuid, p_action_id uuid) returns jsonb
language sql stable set search_path = '' as $$
    select coalesce(jsonb_agg(app_private.material_chunk_json(c) order by c.page, c.chunk_index, c.chunk_id), '[]'::jsonb)
    from app_private.material_chunks c
    where c.user_id = p_uid and c.profile = 'assessment' and exists (
        select 1 from app_private.question_draft_batch_items bi
        join app_private.question_draft_sources qds
          on qds.user_id = bi.user_id and qds.question_id = bi.question_id
        where bi.user_id = p_uid and bi.action_id = p_action_id
          and qds.material_id = c.material_id and qds.chunk_id = c.chunk_id
    )
$$;


create or replace function app_private.material_detail(r app_private.materials) returns jsonb
language sql stable set search_path = '' as $$
select jsonb_build_object('material',app_private.material_json(r),'chunks',coalesce((
 select jsonb_agg(app_private.material_chunk_json(c) order by c.chunk_index)
 from app_private.material_chunks c where c.material_id=r.material_id and c.user_id=r.user_id and c.profile='assessment'),'[]'::jsonb))
$$;


create or replace function app_api.get_assessment_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'get_assessment_material','MaterialLookupArguments');
 a jsonb := p_request->'arguments'; r app_private.materials;
begin
 if e is not null then return e; end if;
 select * into r from app_private.materials where material_id=(a->>'material_id')::uuid
  and user_id=app_private.current_uid() and conversation_id=(a->>'conversation_id')::uuid
  and (not learning_origin or status='READY');
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Material not found.'); end if;
 return app_private.ok_result(p_request,'READ',app_private.material_detail(r));
end $$;


create or replace function app_api.search_material_chunks(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'search_material_chunks','SearchMaterialChunksArguments');
 a jsonb := p_request->'arguments'; items jsonb; q tsquery;
begin
 if e is not null then return e; end if;
 if not exists (select 1 from app_private.materials where material_id=(a->>'material_id')::uuid
  and user_id=app_private.current_uid() and status='READY') then
  return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Material not found.'); end if;
 if a->>'query' is not null then q := plainto_tsquery('simple'::regconfig,a->>'query'); end if;
 select coalesce(jsonb_agg(x.item order by x.rank desc,x.chunk_index),'[]'::jsonb) into items from (
  select app_private.material_chunk_json(c) as item,c.chunk_index,
   case when q is null then 0 else ts_rank_cd(c.search_vector,q) end as rank
  from app_private.material_chunks c where c.material_id=(a->>'material_id')::uuid and c.user_id=app_private.current_uid()
   and c.profile='assessment'
   and (a->>'topic' is null or c.topic=a->>'topic') and (q is null or c.search_vector @@ q)
  order by rank desc,c.chunk_index limit (a->>'limit')::integer
 ) x;
 return app_private.ok_result(p_request,'READ',jsonb_build_object('material_id',a->'material_id','items',items));
end $$;


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
             and c.chunk_id = s.cid::uuid and c.profile = 'assessment' and c.topic = v_draft ->> 'topic';
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
