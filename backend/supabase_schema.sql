create table if not exists documents (
    id uuid primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    filename text not null,
    page_count int not null,
    uploaded_at timestamptz not null default now()
);

create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    session_id uuid not null,
    document_ids uuid[] not null default '{}',
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists sources (
    id uuid primary key default gen_random_uuid(),
    message_id uuid not null references chat_messages (id) on delete cascade,
    document_id uuid not null references documents (id) on delete cascade,
    page int not null,
    excerpt text not null
);

create index if not exists idx_documents_user on documents (user_id);
create index if not exists idx_chat_messages_session on chat_messages (session_id, user_id);
create index if not exists idx_sources_message on sources (message_id);

alter table documents enable row level security;
alter table chat_messages enable row level security;
alter table sources enable row level security;

create policy "Users manage own documents" on documents
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "Users manage own chat messages" on chat_messages
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "Users read sources of own messages" on sources
    for select using (
        exists (
            select 1 from chat_messages
            where chat_messages.id = sources.message_id
            and chat_messages.user_id = auth.uid()
        )
    );
