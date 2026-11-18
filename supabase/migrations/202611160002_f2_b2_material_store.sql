-- F2 B2 only: atomic material/chunk storage and owner-scoped full-text retrieval.
create table app_private.materials (
    material_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id),
    conversation_id uuid not null,
    assessment_version text not null default '1.0.0' check (assessment_version = '1.0.0'),
    filename text not null check (length(btrim(filename)) between 1 and 255),
    mime_type text not null check (mime_type in ('text/plain','text/markdown','application/pdf')),
    size_bytes integer not null check (size_bytes between 1 and 10485760),
    sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
    page_count integer not null check (page_count between 1 and 100),
    char_count integer not null check (char_count between 1 and 200000),
    topics jsonb not null check (jsonb_typeof(topics) = 'array' and jsonb_array_length(topics) = 1),
    status text not null default 'UPLOADED' check (status in ('UPLOADED','READY','FAILED')),
    error_code text check (error_code in ('INVALID_PARAMETER','SERVICE_UNAVAILABLE','INTERNAL_ERROR')),
    upload_fingerprint text not null,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, material_id),
    foreign key (user_id, conversation_id) references app_private.conversation_records(user_id, conversation_id),
    check ((status = 'FAILED') = (error_code is not null))
);

create table app_private.material_chunks (
    chunk_id uuid primary key,
    material_id uuid not null,
    user_id uuid not null,
    page integer not null check (page between 1 and 100),
    topic text not null check (length(btrim(topic)) between 1 and 120),
    chunk_index integer not null check (chunk_index between 0 and 499),
    text text not null check (length(text) between 1 and 4000 and text ~ '\S'),
    search_vector tsvector generated always as (to_tsvector('simple'::regconfig, text)) stored,
    created_at timestamptz not null,
    foreign key (user_id, material_id) references app_private.materials(user_id, material_id),
    unique (material_id, chunk_index)
);
create index material_chunks_search on app_private.material_chunks using gin (search_vector);
create index materials_owner_conversation on app_private.materials(user_id, conversation_id);
create index material_chunks_owner_topic on app_private.material_chunks(user_id, material_id, topic);

alter table app_private.materials enable row level security;
alter table app_private.materials force row level security;
alter table app_private.material_chunks enable row level security;
alter table app_private.material_chunks force row level security;
revoke all on app_private.materials, app_private.material_chunks from public, anon, authenticated;
grant select, insert, update on app_private.materials to sf_rpc_owner;
grant select, insert on app_private.material_chunks to sf_rpc_owner;
create policy materials_select on app_private.materials for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy materials_insert on app_private.materials for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy materials_update on app_private.materials for update to sf_rpc_owner using (user_id = app_private.current_uid()) with check (user_id = app_private.current_uid());
create policy chunks_select on app_private.material_chunks for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy chunks_insert on app_private.material_chunks for insert to sf_rpc_owner with check (user_id = app_private.current_uid());

create function app_private.guard_material_content() returns trigger
language plpgsql set search_path = '' as $$
begin
 if tg_table_name = 'materials' then
  if old.status = 'READY' then raise exception 'READY material is immutable' using errcode='23514'; end if;
  if tg_op = 'UPDATE' and new.status = 'READY' and not exists (
   select 1 from app_private.material_chunks where material_id = new.material_id and user_id = new.user_id
  ) then raise exception 'READY material needs chunks' using errcode='23514'; end if;
 else
  if tg_op <> 'INSERT' then raise exception 'Chunks are immutable' using errcode='23514'; end if;
  if not exists (select 1 from app_private.materials where material_id=new.material_id and user_id=new.user_id
   and status='UPLOADED' and new.page <= page_count and topics ? new.topic) then
   raise exception 'Chunk provenance mismatch' using errcode='23514'; end if;
 end if;
 if tg_op = 'DELETE' then return old; end if;
 return new;
end $$;
create trigger material_immutable before update or delete on app_private.materials
 for each row execute function app_private.guard_material_content();
create trigger chunk_immutable before insert or update or delete on app_private.material_chunks
 for each row execute function app_private.guard_material_content();

create function app_private.material_json(r app_private.materials) returns jsonb
language sql stable set search_path = '' as $$
select jsonb_build_object('assessment_version',r.assessment_version,'material_id',r.material_id,'user_id',r.user_id,
 'conversation_id',r.conversation_id,'filename',r.filename,'mime_type',r.mime_type,'size_bytes',r.size_bytes,
 'sha256',r.sha256,'page_count',r.page_count,'char_count',r.char_count,'topics',r.topics,'status',r.status,
 'error_code',r.error_code,'created_at',app_private.iso(r.created_at),'updated_at',app_private.iso(r.updated_at))
$$;
create function app_private.material_chunk_json(r app_private.material_chunks) returns jsonb
language sql stable set search_path = '' as $$
select jsonb_build_object('chunk_id',r.chunk_id,'material_id',r.material_id,'user_id',r.user_id,
 'page',r.page,'topic',r.topic,'chunk_index',r.chunk_index,'text',r.text,'created_at',app_private.iso(r.created_at))
$$;
create function app_private.material_detail(r app_private.materials) returns jsonb
language sql stable set search_path = '' as $$
select jsonb_build_object('material',app_private.material_json(r),'chunks',coalesce((
 select jsonb_agg(app_private.material_chunk_json(c) order by c.chunk_index)
 from app_private.material_chunks c where c.material_id=r.material_id and c.user_id=r.user_id),'[]'::jsonb))
$$;

create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
select p_routine in ('search_tasks','get_study_plan','get_scheduling_context','lookup_operation_result',
 'list_time_windows','get_workflow_context','get_workflow_continuation','get_ingestion_source',
 'get_assessment_material','search_material_chunks')
$$;

create function app_api.store_assessment_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
 e jsonb := app_private.precheck(p_request,'store_assessment_material','StoreMaterialArguments');
 a jsonb := p_request->'arguments'; uid uuid := app_private.current_uid();
 r app_private.materials; item jsonb; fingerprint text; chars integer := 0; idx integer := 0;
begin
 if e is not null then return e; end if;
 if a->>'conversation_id' is distinct from p_request#>>'{execution_context,conversation_id}' then
  return app_private.error_result(p_request,'INVALID_PARAMETER','Conversation mismatch.'); end if;
 if jsonb_array_length(a->'topics') <> 1 or (a->>'page_count')::integer > 100
  or (a->>'char_count')::integer > 200000 then
  return app_private.error_result(p_request,'INVALID_PARAMETER','B2 supports one topic, 100 pages and 200000 characters.'); end if;
 -- Validate every chunk before any write: a domain error does not roll back.
 for item in select value from jsonb_array_elements(a->'chunks') loop
  if item->>'user_id' is distinct from uid::text or item->>'material_id' is distinct from a->>'material_id'
   or not (a->'topics' ? (item->>'topic')) or (item->>'page')::integer > (a->>'page_count')::integer
   or (item->>'chunk_index')::integer <> idx then
   return app_private.error_result(p_request,'INVALID_PARAMETER','Chunk provenance mismatch.'); end if;
  chars := chars + length(item->>'text'); idx := idx + 1;
 end loop;
 if chars <> (a->>'char_count')::integer or
  (select count(distinct value->>'chunk_id') from jsonb_array_elements(a->'chunks')) <> idx then
  return app_private.error_result(p_request,'INVALID_PARAMETER','Chunk counts or identifiers mismatch.'); end if;
 fingerprint := encode(extensions.digest(convert_to(app_private.canonical_json((a-'chunks') ||
  jsonb_build_object('chunks',(select jsonb_agg(value-'created_at' order by ord)
  from jsonb_array_elements(a->'chunks') with ordinality as c(value,ord)))),'UTF8'),'sha256'),'hex');
 begin
  perform app_private.lock_owner(uid,p_request);
  select * into r from app_private.materials where material_id=(a->>'material_id')::uuid and user_id=uid;
  if found then
   if r.upload_fingerprint <> fingerprint then
    return app_private.error_result(p_request,'IDEMPOTENCY_CONFLICT','Upload key was used for different content.'); end if;
   return app_private.ok_result(p_request,'READ',app_private.material_detail(r));
  end if;
  -- A material can start a conversation, as in the existing source upload flow.
  insert into app_private.conversation_records(user_id,conversation_id) values(uid,(a->>'conversation_id')::uuid) on conflict do nothing;
  insert into app_private.materials(material_id,user_id,conversation_id,filename,mime_type,size_bytes,sha256,
   page_count,char_count,topics,upload_fingerprint)
  values((a->>'material_id')::uuid,uid,(a->>'conversation_id')::uuid,a->>'filename',a->>'mime_type',
   (a->>'size_bytes')::integer,a->>'sha256',(a->>'page_count')::integer,(a->>'char_count')::integer,a->'topics',fingerprint)
  returning * into r;
  insert into app_private.material_chunks(chunk_id,material_id,user_id,page,topic,chunk_index,text,created_at)
  select (c->>'chunk_id')::uuid,r.material_id,uid,(c->>'page')::integer,c->>'topic',(c->>'chunk_index')::integer,
   c->>'text',(c->>'created_at')::timestamptz from jsonb_array_elements(a->'chunks') c;
  update app_private.materials set status='READY',updated_at=clock_timestamp() where material_id=r.material_id returning * into r;
  return app_private.ok_result(p_request,'COMMITTED',app_private.material_detail(r));
 exception when others then return app_private.failure(p_request,sqlstate); end;
end $$;

create function app_api.get_assessment_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare e jsonb := app_private.precheck(p_request,'get_assessment_material','MaterialLookupArguments');
 a jsonb := p_request->'arguments'; r app_private.materials;
begin
 if e is not null then return e; end if;
 select * into r from app_private.materials where material_id=(a->>'material_id')::uuid
  and user_id=app_private.current_uid() and conversation_id=(a->>'conversation_id')::uuid;
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Material not found.'); end if;
 return app_private.ok_result(p_request,'READ',app_private.material_detail(r));
end $$;

create function app_api.search_material_chunks(p_request jsonb) returns jsonb
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
   and (a->>'topic' is null or c.topic=a->>'topic') and (q is null or c.search_vector @@ q)
  order by rank desc,c.chunk_index limit (a->>'limit')::integer
 ) x;
 return app_private.ok_result(p_request,'READ',jsonb_build_object('material_id',a->'material_id','items',items));
end $$;

alter function app_private.guard_material_content() owner to sf_rpc_owner;
alter function app_private.material_json(app_private.materials) owner to sf_rpc_owner;
alter function app_private.material_chunk_json(app_private.material_chunks) owner to sf_rpc_owner;
alter function app_private.material_detail(app_private.materials) owner to sf_rpc_owner;
revoke all on function app_private.guard_material_content(), app_private.material_json(app_private.materials),
 app_private.material_chunk_json(app_private.material_chunks), app_private.material_detail(app_private.materials) from public, anon, authenticated;
do $$ declare name text; begin
 foreach name in array array['store_assessment_material','get_assessment_material','search_material_chunks'] loop
  execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner',name);
  execute format('revoke all on function app_api.%I(jsonb) from public,anon',name);
  execute format('grant execute on function app_api.%I(jsonb) to authenticated',name);
 end loop;
end $$;
