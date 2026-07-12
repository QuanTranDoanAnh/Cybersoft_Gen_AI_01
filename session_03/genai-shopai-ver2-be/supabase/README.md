# PostgreSQL / Supabase Setup

Run these files in Supabase SQL Editor, or any PostgreSQL client connected to your database:

1. `schema.sql`
2. `seed.sql`

The seed file uses `on conflict` upserts, so you can run it multiple times while developing.

After that, put database access in:

```txt
backend/.env
```

Required values:

```bash
DB_HOST=your-db-host
DB_PORT=5432
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_DATABASE=postgres
DB_SSLMODE=require
```

For Supabase, get them in `Project Settings` > `Database` > `Connection string` or `Connection parameters`.

The schema includes ecommerce data plus v2 auth/memory tables:

- `users`
- `conversations`
- `messages`

The backend automatically uses PostgreSQL when the DB values are present. Otherwise it falls back to mock data, including in-memory users and chat history.
