create extension if not exists vector;

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    content text not null,
    metadata jsonb,
    embedding vector(1536)
);

create index if not exists documents_embedding_idx
    on documents using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create or replace function match_documents(
    query_embedding vector(1536),
    match_count int default 5
)
returns table (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
language sql stable
as $$
    select
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    from documents
    order by documents.embedding <=> query_embedding
    limit match_count;
$$;

create table if not exists sessions (
    id uuid primary key,
    device_id text,
    user_age int,
    locale text,
    created_at timestamptz not null
);

create table if not exists session_events (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete cascade,
    event_type text not null,
    payload jsonb,
    client_ts timestamptz,
    received_at timestamptz not null
);

create index if not exists session_events_session_id_idx
    on session_events(session_id);

create table if not exists tutor_interactions (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete set null,
    question text not null,
    answer text not null,
    grade_level text,
    subject text,
    language text,
    has_image boolean default false,
    guard jsonb,
    created_at timestamptz not null
);

create index if not exists tutor_interactions_session_id_idx
    on tutor_interactions(session_id);
