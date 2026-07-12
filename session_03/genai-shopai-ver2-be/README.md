# ShopAI Assistant v2 Backend

FastAPI backend for products, orders, user auth, per-user conversations, and LangChain chat memory.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs`.

## Environment

```bash
AUTH_SECRET_KEY=change-this-dev-secret
AUTH_TOKEN_TTL_SECONDS=604800

LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
MAX_HISTORY_MESSAGES=16
FRONTEND_ORIGIN=http://localhost:3000

DB_HOST=
DB_PORT=5432
DB_USER=
DB_PASSWORD=
DB_DATABASE=
DB_SSLMODE=require
```

If `OPENAI_API_KEY` or `GROQ_API_KEY` is empty, chat falls back to deterministic rule-based replies.

Do not commit `.env`.
