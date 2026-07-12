import uuid
from datetime import datetime, timezone

from app.schemas.chat import ChatMessage, ChatMode
from app.services.data_service import _connect, postgres_enabled


mock_users_by_id: dict[str, dict] = {}
mock_users_by_email: dict[str, dict] = {}
mock_conversations: dict[str, dict] = {}
mock_messages: dict[str, list[dict]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _iso(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _public_user(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "display_name": row["display_name"],
    }


def _conversation_summary(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "title": row.get("title") or "Cuộc trò chuyện mới",
        "mode": row["mode"],
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row.get("updated_at") or row["created_at"]),
        "message_count": int(row.get("message_count") or 0),
        "last_message": row.get("last_message"),
    }


def get_user_by_email(email: str) -> dict | None:
    normalized_email = _normalize_email(email)
    if not postgres_enabled():
        user = mock_users_by_email.get(normalized_email)
        return _public_user(user) | {"password_hash": user["password_hash"]} if user else None

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, email, display_name, password_hash
                from public.users
                where lower(email) = lower(%s)
                limit 1
                """,
                (normalized_email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    if not postgres_enabled():
        user = mock_users_by_id.get(user_id)
        return _public_user(user) if user else None

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, email, display_name
                from public.users
                where id = %s
                limit 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return _public_user(row) if row else None


def create_user(email: str, display_name: str, password_hash: str) -> dict:
    normalized_email = _normalize_email(email)
    if get_user_by_email(normalized_email):
        raise ValueError("Email này đã được đăng ký.")

    if not postgres_enabled():
        user = {
            "id": str(uuid.uuid4()),
            "email": normalized_email,
            "display_name": display_name.strip(),
            "password_hash": password_hash,
            "created_at": _now_iso(),
        }
        mock_users_by_id[user["id"]] = user
        mock_users_by_email[normalized_email] = user
        return _public_user(user)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.users (email, display_name, password_hash)
                values (%s, %s, %s)
                returning id, email, display_name
                """,
                (normalized_email, display_name.strip(), password_hash),
            )
            return _public_user(cur.fetchone())


def create_conversation(user_id: str, mode: ChatMode, title: str) -> dict:
    now = _now_iso()
    if not postgres_enabled():
        conversation = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "mode": mode.value,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "last_message": None,
        }
        mock_conversations[conversation["id"]] = conversation
        mock_messages[conversation["id"]] = []
        return _conversation_summary(conversation)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.conversations (user_id, mode, title)
                values (%s, %s, %s)
                returning id, mode, title, created_at, updated_at
                """,
                (user_id, mode.value, title),
            )
            row = dict(cur.fetchone())
            row["message_count"] = 0
            row["last_message"] = None
            return _conversation_summary(row)


def get_conversation(user_id: str, conversation_id: str) -> dict | None:
    if not postgres_enabled():
        conversation = mock_conversations.get(conversation_id)
        if not conversation or conversation["user_id"] != user_id:
            return None
        messages = mock_messages.get(conversation_id, [])
        row = dict(conversation)
        row["message_count"] = len(messages)
        row["last_message"] = messages[-1]["content"] if messages else None
        return _conversation_summary(row)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  c.id,
                  c.mode,
                  c.title,
                  c.created_at,
                  c.updated_at,
                  (
                    select count(*)
                    from public.messages m
                    where m.conversation_id = c.id
                  ) as message_count,
                  (
                    select m.content
                    from public.messages m
                    where m.conversation_id = c.id
                    order by m.created_at desc, m.id desc
                    limit 1
                  ) as last_message
                from public.conversations c
                where c.id = %s and c.user_id = %s
                limit 1
                """,
                (conversation_id, user_id),
            )
            row = cur.fetchone()
            return _conversation_summary(row) if row else None


def list_conversations(user_id: str) -> list[dict]:
    if not postgres_enabled():
        rows = []
        for conversation in mock_conversations.values():
            if conversation["user_id"] != user_id:
                continue
            messages = mock_messages.get(conversation["id"], [])
            row = dict(conversation)
            row["message_count"] = len(messages)
            row["last_message"] = messages[-1]["content"] if messages else None
            rows.append(_conversation_summary(row))
        return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  c.id,
                  c.mode,
                  c.title,
                  c.created_at,
                  c.updated_at,
                  count(m.id) as message_count,
                  (
                    select m2.content
                    from public.messages m2
                    where m2.conversation_id = c.id
                    order by m2.created_at desc, m2.id desc
                    limit 1
                  ) as last_message
                from public.conversations c
                left join public.messages m on m.conversation_id = c.id
                where c.user_id = %s
                group by c.id
                order by c.updated_at desc
                """,
                (user_id,),
            )
            return [_conversation_summary(row) for row in cur.fetchall()]


def update_conversation(user_id: str, conversation_id: str, title: str | None = None, mode: ChatMode | None = None) -> dict | None:
    conversation = get_conversation(user_id, conversation_id)
    if not conversation:
        return None

    if not postgres_enabled():
        row = mock_conversations[conversation_id]
        if title is not None:
            row["title"] = title.strip()
        if mode is not None:
            row["mode"] = mode.value
        row["updated_at"] = _now_iso()
        return get_conversation(user_id, conversation_id)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.conversations
                set
                  title = coalesce(%s, title),
                  mode = coalesce(%s, mode),
                  updated_at = now()
                where id = %s and user_id = %s
                returning id
                """,
                (title.strip() if title is not None else None, mode.value if mode is not None else None, conversation_id, user_id),
            )
            if not cur.fetchone():
                return None
    return get_conversation(user_id, conversation_id)


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    if not get_conversation(user_id, conversation_id):
        return False

    if not postgres_enabled():
        mock_conversations.pop(conversation_id, None)
        mock_messages.pop(conversation_id, None)
        return True

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from public.conversations where id = %s and user_id = %s",
                (conversation_id, user_id),
            )
            return cur.rowcount > 0


def list_messages(conversation_id: str) -> list[ChatMessage]:
    if not postgres_enabled():
        return [ChatMessage(role=item["role"], content=item["content"]) for item in mock_messages.get(conversation_id, [])]

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select role, content
                from public.messages
                where conversation_id = %s
                order by created_at asc, id asc
                """,
                (conversation_id,),
            )
            return [ChatMessage(role=row["role"], content=row["content"]) for row in cur.fetchall()]


def append_message(conversation_id: str, role: str, content: str) -> None:
    if not postgres_enabled():
        messages = mock_messages.setdefault(conversation_id, [])
        messages.append({"role": role, "content": content, "created_at": _now_iso()})
        if conversation_id in mock_conversations:
            mock_conversations[conversation_id]["updated_at"] = _now_iso()
        return

    with _connect() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.messages (conversation_id, role, content)
                    values (%s, %s, %s)
                    """,
                    (conversation_id, role, content),
                )
                cur.execute(
                    "update public.conversations set updated_at = now() where id = %s",
                    (conversation_id,),
                )


def clear_messages(conversation_id: str) -> None:
    if not postgres_enabled():
        mock_messages[conversation_id] = []
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from public.messages where conversation_id = %s", (conversation_id,))
