create extension if not exists pgcrypto;

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  display_name text not null,
  password_hash text not null,
  created_at timestamptz not null default now()
);

alter table public.conversations
add column if not exists title text not null default 'Cuộc trò chuyện mới';

alter table public.conversations
add column if not exists updated_at timestamptz not null default now();

-- Nếu có conversation cũ từ bản 1.2 không gắn user, xoá phần chat cũ để tránh lỗi NOT NULL/FK.
delete from public.messages
where conversation_id in (
  select id from public.conversations where user_id is null
);

delete from public.conversations
where user_id is null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'conversations_user_id_fkey'
  ) then
    alter table public.conversations
    add constraint conversations_user_id_fkey
    foreign key (user_id)
    references public.users(id)
    on delete cascade;
  end if;
end $$;

alter table public.conversations
alter column user_id set not null;

create index if not exists idx_conversations_user_id
on public.conversations(user_id);

create index if not exists idx_conversations_updated_at
on public.conversations(updated_at desc);