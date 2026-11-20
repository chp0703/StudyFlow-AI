-- F3 M1 extends the canonical F2 library and preserves all existing identities.
create extension if not exists vector with schema extensions;

alter table app_private.materials
    add column learning_status text check (learning_status in ('UPLOADED','INDEXING','READY','FAILED')),
    add column learning_error text check (learning_error in ('INVALID_DOCUMENT','INDEX_TIMEOUT','INDEX_UNAVAILABLE')),
    add column course_label text check (length(course_label) between 1 and 120 and course_label ~ '\S'),
    add column learning_origin boolean not null default false,
    add column learning_claim uuid,
    add column learning_deadline timestamptz,
    add constraint materials_learning_failure_shape check (
        (learning_status is not distinct from 'FAILED') = (learning_error is not null)
    ),
    add constraint materials_learning_claim_check check (
        (learning_status is not distinct from 'INDEXING') = (learning_claim is not null)
        and (learning_claim is null) = (learning_deadline is null)
    ),
    add constraint materials_learning_limits check (
        learning_status is null or (size_bytes <= 5242880 and page_count <= 50)
    );

create index materials_owner_sha256 on app_private.materials(user_id, sha256, created_at, material_id);
create index materials_learning_list on app_private.materials(user_id, created_at desc, material_id desc)
    where learning_status is not null;

alter table app_private.material_chunks
    drop constraint material_chunks_material_id_chunk_index_key,
    drop constraint material_chunks_chunk_index_check,
    add column profile text not null default 'assessment' check (profile in ('assessment','learning')),
    add column learning_ordinal integer check (learning_ordinal >= 0),
    add column embedding extensions.vector(384),
    add column embedding_model text,
    add constraint material_chunks_profile_index_key unique (material_id, profile, chunk_index),
    add constraint material_chunks_learning_ordinal_key unique (material_id, learning_ordinal),
    add constraint material_chunks_profile_bounds check (
        chunk_index >= 0 and (profile <> 'assessment' or chunk_index <= 499)
        and (profile <> 'learning' or learning_ordinal is not null)
    ),
    add constraint material_chunks_learning_embedding_check check (
        (learning_ordinal is null and embedding is null and embedding_model is null)
        or (learning_ordinal is not null and embedding is not null
            and embedding_model is not distinct from 'intfloat/multilingual-e5-small'
            and abs(extensions.vector_norm(embedding) - 1) <= 0.0001
            and page <= 50 and length(text) <= 1600)
    );

create index material_chunks_learning_cosine on app_private.material_chunks
    using hnsw (embedding extensions.vector_cosine_ops) where embedding is not null;

create table app_private.learning_material_receipts (
    user_id uuid not null references app_private.user_profiles(user_id),
    operation text not null check (operation in ('upload','delete')),
    idempotency_key text not null check (idempotency_key ~ '^[A-Za-z0-9._:-]{16,128}$'),
    fingerprint text not null check (fingerprint ~ '^[0-9a-f]{64}$'),
    material_id uuid not null,
    claim uuid unique,
    response jsonb,
    primary key (user_id, operation, idempotency_key),
    check ((claim is null) = (response is not null))
);

create table app_private.learning_session (
    session_id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_private.user_profiles(user_id),
    conversation_id uuid not null,
    goal text not null check (length(goal) between 1 and 1000 and goal ~ '\S'),
    material_ids uuid[] not null check (cardinality(material_ids) between 1 and 5),
    planner_block_id uuid,
    status text not null default 'ACTIVE' check (status in ('ACTIVE','SUMMARY_PENDING','CLOSED')),
    version bigint not null default 1 check (version >= 1),
    created_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null default (clock_timestamp() + interval '30 days'),
    unique (user_id, session_id),
    foreign key (user_id, conversation_id) references app_private.conversation_records(user_id, conversation_id),
    check (expires_at > created_at)
);

create table app_private.learning_turn (
    turn_id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    session_id uuid not null,
    ordinal bigint not null check (ordinal >= 1),
    role text not null check (role in ('USER','ASSISTANT')),
    kind text not null check (kind in ('ASK','HINT')),
    hint_level integer check (hint_level between 1 and 3 and kind = 'HINT' and role = 'ASSISTANT'),
    content text not null check (length(content) between 1 and 12000 and content ~ '\S'),
    -- Citation snapshots retain IDs after material deletion.
    citations jsonb not null default '[]'::jsonb check (jsonb_typeof(citations) = 'array'),
    supported boolean,
    model text,
    prompt_version text,
    created_at timestamptz not null default clock_timestamp(),
    unique (session_id, ordinal),
    foreign key (user_id, session_id) references app_private.learning_session(user_id, session_id) on delete cascade,
    check ((role = 'USER') = (supported is null))
);

create table app_private.session_outcome (
    outcome_id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    session_id uuid not null unique,
    summary text not null check (length(summary) between 1 and 12000 and summary ~ '\S'),
    topics text[] not null,
    duration_minutes bigint not null check (duration_minutes >= 0),
    confirmed_at timestamptz not null default clock_timestamp(),
    foreign key (user_id, session_id) references app_private.learning_session(user_id, session_id)
);

create function app_private.guard_session_outcome() returns trigger
language plpgsql set search_path = '' as $$
begin
    raise exception 'Session outcome is immutable' using errcode = '23514';
end
$$;
create trigger session_outcome_immutable before update or delete on app_private.session_outcome
    for each row execute function app_private.guard_session_outcome();
revoke all on function app_private.guard_session_outcome() from public, anon, authenticated;

do $$
declare relation text;
begin
    foreach relation in array array['learning_material_receipts','learning_session','learning_turn','session_outcome'] loop
        execute format('alter table app_private.%I enable row level security', relation);
        execute format('alter table app_private.%I force row level security', relation);
        execute format('revoke all on app_private.%I from public, anon, authenticated', relation);
        execute format('create policy learning_owner on app_private.%I to sf_rpc_owner using (user_id = app_private.current_uid()) with check (user_id = app_private.current_uid())', relation);
    end loop;
end
$$;

grant select, insert, update on app_private.learning_material_receipts to sf_rpc_owner;
grant select on app_private.learning_session, app_private.learning_turn, app_private.session_outcome to sf_rpc_owner;
