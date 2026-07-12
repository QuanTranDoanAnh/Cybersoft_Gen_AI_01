create extension if not exists pgcrypto;

create table if not exists public.products (
  id text primary key,
  name text not null,
  slug text not null unique,
  description text not null,
  price integer not null check (price >= 0),
  original_price integer check (original_price is null or original_price >= price),
  category text not null,
  rating numeric(2, 1) not null default 0 check (rating >= 0 and rating <= 5),
  sold_count integer not null default 0 check (sold_count >= 0),
  stock integer not null default 0 check (stock >= 0),
  image_url text not null,
  variants text[] not null default '{}',
  tags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.faqs (
  id text primary key,
  category text not null,
  question text not null,
  answer text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.orders (
  id text primary key,
  customer_name text not null,
  phone text not null,
  address text not null,
  status text not null check (status in ('Chờ xác nhận', 'Đang xử lý', 'Đang giao', 'Đã giao', 'Đã hủy')),
  total_amount integer not null default 0 check (total_amount >= 0),
  created_at timestamptz not null default now()
);

create table if not exists public.order_items (
  id bigserial primary key,
  order_id text not null references public.orders(id) on delete cascade,
  product_id text not null references public.products(id),
  quantity integer not null check (quantity > 0),
  price integer not null check (price >= 0),
  created_at timestamptz not null default now(),
  unique (order_id, product_id)
);

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  display_name text not null,
  password_hash text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  mode text not null check (mode in ('with_context', 'without_context')),
  title text not null default 'Cuộc trò chuyện mới',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_products_category on public.products(category);
create index if not exists idx_products_tags on public.products using gin(tags);
create index if not exists idx_order_items_order_id on public.order_items(order_id);
create index if not exists idx_conversations_user_id on public.conversations(user_id);
create index if not exists idx_messages_conversation_id on public.messages(conversation_id);
