-- BE-04 1.0.0: private source metadata, bounded bytes, extraction leases and lineage.
-- This adds no domain mutation or approval bypass. Existing migrations remain immutable.

create table app_private.ingestion_sources (
    source_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id),
    conversation_id uuid not null,
    ingestion_version text not null default '1.0.0' check (ingestion_version = '1.0.0'),
    filename text not null check (length(filename) between 1 and 255),
    mime_type text not null,
    size_bytes bigint not null check (size_bytes between 1 and 5242880),
    sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
    content bytea,
    status text not null default 'UPLOADED' check (status in ('UPLOADED','EXTRACTING','READY','FAILED')),
    lease_version bigint not null default 0 check (lease_version >= 0),
    lease_until timestamptz,
    extraction jsonb,
    error_code text check (error_code in ('INVALID_PARAMETER','SERVICE_UNAVAILABLE','INTERNAL_ERROR')),
    created_at timestamptz not null default clock_timestamp(),
    unique (user_id, conversation_id, source_id),
    foreign key (user_id, conversation_id) references app_private.conversation_records(user_id, conversation_id),
    check ((status = 'READY' and extraction is not null and content is null and error_code is null)
        or (status <> 'READY' and extraction is null and content is not null)),
    check ((status = 'EXTRACTING') = (lease_until is not null))
);

create table app_private.message_source_links (
    user_id uuid not null,
    message_id uuid not null,
    source_id uuid not null,
    conversation_id uuid not null,
    primary key (user_id, message_id, source_id),
    foreign key (user_id, message_id) references app_private.source_messages(user_id, message_id),
    foreign key (user_id, conversation_id, source_id) references app_private.ingestion_sources(user_id, conversation_id, source_id)
);
alter table app_private.ingestion_sources enable row level security;
alter table app_private.ingestion_sources force row level security;
alter table app_private.message_source_links enable row level security;
alter table app_private.message_source_links force row level security;
revoke all on app_private.ingestion_sources, app_private.message_source_links from public, anon, authenticated;
grant select, insert, update on app_private.ingestion_sources to sf_rpc_owner;
grant select, insert on app_private.message_source_links to sf_rpc_owner;
create policy ingestion_owner_select on app_private.ingestion_sources for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy ingestion_owner_insert on app_private.ingestion_sources for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy ingestion_owner_update on app_private.ingestion_sources for update to sf_rpc_owner using (user_id = app_private.current_uid()) with check (user_id = app_private.current_uid());
create policy source_links_select on app_private.message_source_links for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy source_links_insert on app_private.message_source_links for insert to sf_rpc_owner with check (user_id = app_private.current_uid());

create function app_private.ingestion_source_json(r app_private.ingestion_sources) returns jsonb
language sql stable set search_path = '' as $$
select jsonb_build_object('ingestion_version',r.ingestion_version,'source_id',r.source_id,'user_id',r.user_id,
 'conversation_id',r.conversation_id,'filename',r.filename,'mime_type',r.mime_type,'size_bytes',r.size_bytes,
 'sha256',r.sha256,'status',r.status,'lease_version',r.lease_version,'created_at',app_private.iso(r.created_at),
 'extraction',r.extraction,'error_code',r.error_code)
$$;

create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
select p_routine in ('search_tasks','get_study_plan','get_scheduling_context','lookup_operation_result',
 'list_time_windows','get_workflow_context','get_workflow_continuation','get_ingestion_source')
$$;

create function app_api.store_ingestion_source(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
 e jsonb := app_private.precheck(p_request,'store_ingestion_source','StoreSourceArguments');
 a jsonb := p_request->'arguments'; uid uuid := app_private.current_uid();
 r app_private.ingestion_sources; bytes bytea;
begin
 if e is not null then return e; end if;
 if a->>'conversation_id' is distinct from p_request#>>'{execution_context,conversation_id}' then
  return app_private.error_result(p_request,'INVALID_PARAMETER','Conversation mismatch.'); end if;
 begin
  bytes := decode(a->>'content_base64','base64');
  if octet_length(bytes) is distinct from (a->>'size_bytes')::bigint
    or encode(extensions.digest(bytes,'sha256'),'hex') is distinct from a->>'sha256' then
   return app_private.error_result(p_request,'INVALID_PARAMETER','Source digest or length mismatch.'); end if;
  perform app_private.lock_owner(uid,p_request);
  select * into r from app_private.ingestion_sources where source_id=(a->>'source_id')::uuid and user_id=uid;
  if found then
   if (r.conversation_id,r.filename,r.mime_type,r.sha256,r.size_bytes) is distinct from
      ((a->>'conversation_id')::uuid,a->>'filename',a->>'mime_type',a->>'sha256',(a->>'size_bytes')::bigint) then
    return app_private.error_result(p_request,'IDEMPOTENCY_CONFLICT','Upload key was used for different content.'); end if;
   return app_private.ok_result(p_request,'READ',app_private.ingestion_source_json(r));
  end if;
  insert into app_private.conversation_records(user_id,conversation_id) values(uid,(a->>'conversation_id')::uuid) on conflict do nothing;
  insert into app_private.ingestion_sources(source_id,user_id,conversation_id,filename,mime_type,size_bytes,sha256,content)
   values((a->>'source_id')::uuid,uid,(a->>'conversation_id')::uuid,a->>'filename',a->>'mime_type',(a->>'size_bytes')::bigint,a->>'sha256',bytes) returning * into r;
  return app_private.ok_result(p_request,'COMMITTED',app_private.ingestion_source_json(r));
 exception when others then return app_private.failure(p_request,sqlstate); end;
end $$;

create function app_api.get_ingestion_source(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'get_ingestion_source','SourceLookupArguments'); a jsonb := p_request->'arguments'; r app_private.ingestion_sources;
begin
 if e is not null then return e; end if;
 select * into r from app_private.ingestion_sources where source_id=(a->>'source_id')::uuid
  and user_id=app_private.current_uid() and conversation_id=(a->>'conversation_id')::uuid;
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Source not found.'); end if;
 return app_private.ok_result(p_request,'READ',app_private.ingestion_source_json(r));
end $$;

create function app_api.claim_source_extraction(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'claim_source_extraction','SourceLookupArguments'); a jsonb := p_request->'arguments'; r app_private.ingestion_sources;
begin
 if e is not null then return e; end if;
 select * into r from app_private.ingestion_sources where source_id=(a->>'source_id')::uuid
  and user_id=app_private.current_uid() and conversation_id=(a->>'conversation_id')::uuid for update;
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Source not found.'); end if;
 if r.status='READY' then return app_private.ok_result(p_request,'READ',jsonb_build_object('source',app_private.ingestion_source_json(r),'content_base64',null)); end if;
 if r.status='EXTRACTING' and r.lease_until > clock_timestamp() then
  return app_private.error_result(p_request,'SERVICE_UNAVAILABLE','Source extraction is already running.'); end if;
 update app_private.ingestion_sources set status='EXTRACTING',lease_version=lease_version+1,
  lease_until=clock_timestamp()+interval '120 seconds',error_code=null where source_id=r.source_id returning * into r;
 return app_private.ok_result(p_request,'COMMITTED',jsonb_build_object('source',app_private.ingestion_source_json(r),
  'content_base64',replace(encode(r.content,'base64'),E'\n','')));
end $$;

create function app_api.complete_source_extraction(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'complete_source_extraction','CompleteSourceExtractionArguments');
 a jsonb := p_request->'arguments'; r app_private.ingestion_sources; item jsonb;
begin
 if e is not null then return e; end if;
 select * into r from app_private.ingestion_sources where source_id=(a->>'source_id')::uuid
  and user_id=app_private.current_uid() and conversation_id=(a->>'conversation_id')::uuid for update;
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Source not found.'); end if;
 if r.lease_version is distinct from (a->>'expected_lease_version')::bigint then
  return app_private.error_result(p_request,'STALE_ENTITY_VERSION','Extraction lease changed.'); end if;
 if r.status='READY' and r.extraction = a->'extraction' then
  return app_private.ok_result(p_request,'READ',app_private.ingestion_source_json(r)); end if;
 if r.status<>'EXTRACTING' or r.lease_until <= clock_timestamp() then
  return app_private.error_result(p_request,'STALE_ENTITY_VERSION','Extraction lease expired.'); end if;
 if (a->'extraction' = 'null'::jsonb) = (a->'error_code' = 'null'::jsonb) then
  return app_private.error_result(p_request,'INVALID_PARAMETER','Exactly one extraction result or error is required.'); end if;
 if a->'extraction' <> 'null'::jsonb then
  for item in select value from jsonb_array_elements(a#>'{extraction,intents}') loop
   if item->>'intent' is distinct from case when r.mime_type in ('text/calendar','text/csv') then 'SET_BUSY_INTERVAL' else 'CREATE_TASK' end then
    return app_private.error_result(p_request,'INVALID_PARAMETER','Source intent does not match its media type.'); end if;
  end loop;
 end if;
 update app_private.ingestion_sources set status=case when a->'extraction'='null'::jsonb then 'FAILED' else 'READY' end,
  extraction=nullif(a->'extraction','null'::jsonb), error_code=a->>'error_code',lease_until=null,
  content=case when a->'extraction'='null'::jsonb then content else null end where source_id=r.source_id returning * into r;
 return app_private.ok_result(p_request,'COMMITTED',app_private.ingestion_source_json(r));
end $$;

-- Keep the BE-03 implementation private; the wrapper binds validated source IDs
-- atomically to its immutable source message. Its original precheck stays active.
alter function app_api.record_source_message(jsonb) rename to record_source_message_be03;
alter function app_api.record_source_message_be03(jsonb) set schema app_private;
revoke all on function app_private.record_source_message_be03(jsonb) from public,anon,authenticated;

create function app_api.record_source_message(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'record_source_message','RecordSourceMessageArguments');
 a jsonb := p_request->'arguments'; uid uuid := app_private.current_uid();
 conv uuid; msg uuid;
 ids jsonb := coalesce(a->'source_ids','[]'::jsonb); id text; old_ids jsonb; result jsonb;
begin
 if e is not null then return e; end if;
 conv := (a#>>'{message,conversation_id}')::uuid;
 msg := (a#>>'{message,message_id}')::uuid;
 for id in select jsonb_array_elements_text(ids) loop
  if not exists(select 1 from app_private.ingestion_sources where user_id=uid and conversation_id=conv and source_id=id::uuid and status='READY') then
   return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Ready source not found.'); end if;
 end loop;
 if exists(select 1 from app_private.source_messages where user_id=uid and message_id=msg) then
  select coalesce(jsonb_agg(source_id::text order by source_id::text),'[]'::jsonb) into old_ids
   from app_private.message_source_links where user_id=uid and message_id=msg;
  if old_ids <> (select coalesce(jsonb_agg(value order by value),'[]'::jsonb) from jsonb_array_elements_text(ids)) then
   return app_private.error_result(p_request,'IDEMPOTENCY_CONFLICT','Message source references changed.'); end if;
 end if;
 begin
  result := app_private.record_source_message_be03(p_request);
  if result->>'outcome'='ERROR' then return result; end if;
  insert into app_private.message_source_links(user_id,message_id,source_id,conversation_id)
   select uid,msg,value::uuid,conv from jsonb_array_elements_text(ids) on conflict do nothing;
  return result;
 exception when others then return app_private.failure(p_request,sqlstate); end;
end $$;

alter function app_private.ingestion_source_json(app_private.ingestion_sources) owner to sf_rpc_owner;
revoke all on function app_private.ingestion_source_json(app_private.ingestion_sources) from public,anon,authenticated;
do $$ declare name text; begin
 foreach name in array array['store_ingestion_source','get_ingestion_source','claim_source_extraction','complete_source_extraction','record_source_message'] loop
  execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner',name);
  execute format('revoke all on function app_api.%I(jsonb) from public,anon',name);
  execute format('grant execute on function app_api.%I(jsonb) to authenticated',name);
 end loop;
end $$;
