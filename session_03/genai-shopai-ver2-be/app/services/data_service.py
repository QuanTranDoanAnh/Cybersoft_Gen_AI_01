import os
import re
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from app.schemas.order import CreateOrderRequest
from app.services import mock_data

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DATABASE = os.getenv("DB_DATABASE", "")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")


def postgres_enabled() -> bool:
    return bool(DB_HOST and DB_PORT and DB_USER and DB_PASSWORD and DB_DATABASE)


def _connect():
    kwargs = {
        "host": DB_HOST,
        "port": int(DB_PORT),
        "user": DB_USER,
        "password": DB_PASSWORD,
        "dbname": DB_DATABASE,
        "row_factory": dict_row,
    }
    if DB_SSLMODE:
        kwargs["sslmode"] = DB_SSLMODE
    return psycopg.connect(**kwargs)


def _normalize_product(row: dict) -> dict:
    product = dict(row)
    product["rating"] = float(product.get("rating") or 0)
    product["variants"] = product.get("variants") or []
    product["tags"] = product.get("tags") or []
    return product


def _normalize_order(row: dict, items: list[dict]) -> dict:
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "phone": row["phone"],
        "address": row["address"],
        "status": row["status"],
        "total_amount": row["total_amount"],
        "items": items,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }


def _filter_mock_products(products: list[dict], search: str | None = None, category: str | None = None):
    filtered = products

    if category and category != "Tất cả":
        filtered = [product for product in filtered if product["category"] == category]

    if search:
        keyword = search.lower().strip()
        filtered = [
            product
            for product in filtered
            if keyword in product["name"].lower()
            or keyword in product["description"].lower()
            or keyword in " ".join(product.get("tags", [])).lower()
        ]

    return filtered


def list_products(search: str | None = None, category: str | None = None) -> list[dict]:
    if not postgres_enabled():
        return _filter_mock_products(mock_data.PRODUCTS, search, category)

    category_filter = None if not category or category == "Tất cả" else category
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  id,
                  name,
                  slug,
                  description,
                  price,
                  original_price,
                  category,
                  rating,
                  sold_count,
                  stock,
                  image_url,
                  variants,
                  tags
                from public.products
                where (%s::text is null or category = %s::text)
                  and (
                    %s::text is null
                    or name ilike %s::text
                    or description ilike %s::text
                    or array_to_string(tags, ' ') ilike %s::text
                  )
                order by sold_count desc, id asc
                """,
                (
                    category_filter,
                    category_filter,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                ),
            )
            return [_normalize_product(row) for row in cur.fetchall()]


def get_categories() -> list[str]:
    if not postgres_enabled():
        return sorted({product["category"] for product in mock_data.PRODUCTS})

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select distinct category from public.products order by category asc")
            return [row["category"] for row in cur.fetchall()]


def get_product(product_id_or_slug: str) -> dict | None:
    if not postgres_enabled():
        return mock_data.get_product(product_id_or_slug)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  id,
                  name,
                  slug,
                  description,
                  price,
                  original_price,
                  category,
                  rating,
                  sold_count,
                  stock,
                  image_url,
                  variants,
                  tags
                from public.products
                where id = %s or slug = %s
                limit 1
                """,
                (product_id_or_slug, product_id_or_slug),
            )
            row = cur.fetchone()
            return _normalize_product(row) if row else None


def list_faqs() -> list[dict]:
    if not postgres_enabled():
        return mock_data.FAQS

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, category, question, answer
                from public.faqs
                order by category asc, id asc
                """
            )
            return cur.fetchall()


def _get_order_items(conn, order_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              oi.product_id,
              coalesce(p.name, oi.product_id) as product_name,
              oi.quantity,
              oi.price
            from public.order_items oi
            left join public.products p on p.id = oi.product_id
            where oi.order_id = %s
            order by oi.id asc
            """,
            (order_id,),
        )
        return cur.fetchall()


def list_orders(limit: int = 20) -> list[dict]:
    if not postgres_enabled():
        return mock_data.ORDERS[:limit]

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, customer_name, phone, address, status, total_amount, created_at
                from public.orders
                order by created_at desc
                limit %s
                """,
                (limit,),
            )
            orders = cur.fetchall()

        return [_normalize_order(order, _get_order_items(conn, order["id"])) for order in orders]


def get_order(order_id: str) -> dict | None:
    if not postgres_enabled():
        return mock_data.get_order(order_id)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, customer_name, phone, address, status, total_amount, created_at
                from public.orders
                where lower(id) = lower(%s)
                limit 1
                """,
                (order_id,),
            )
            order = cur.fetchone()

        if not order:
            return None

        return _normalize_order(order, _get_order_items(conn, order["id"]))


def _next_order_id(conn) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            select coalesce(max((substring(id from 'OD([0-9]+)'))::integer), 1000) as max_number
            from public.orders
            where id ~ '^OD[0-9]+$'
            """
        )
        row = cur.fetchone()
        return f"OD{row['max_number'] + 1}"


def create_order(payload: CreateOrderRequest) -> dict:
    if not postgres_enabled():
        return _create_mock_order(payload)

    with _connect() as conn:
        with conn.transaction():
            order_items = []
            total_amount = 0

            for item in payload.items:
                product = get_product(item.product_id)
                if not product:
                    raise ValueError(f"Product {item.product_id} not found")
                if item.quantity > product["stock"]:
                    raise ValueError(f"Product {product['name']} is out of stock")

                order_items.append(
                    {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "quantity": item.quantity,
                        "price": product["price"],
                    }
                )
                total_amount += product["price"] * item.quantity

            order_id = _next_order_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.orders (id, customer_name, phone, address, status, total_amount)
                    values (%s, %s, %s, %s, %s, %s)
                    returning id, customer_name, phone, address, status, total_amount, created_at
                    """,
                    (
                        order_id,
                        payload.customer_name,
                        payload.phone,
                        payload.address,
                        "Chờ xác nhận",
                        total_amount,
                    ),
                )
                order = cur.fetchone()

                for item in order_items:
                    cur.execute(
                        """
                        insert into public.order_items (order_id, product_id, quantity, price)
                        values (%s, %s, %s, %s)
                        """,
                        (order_id, item["product_id"], item["quantity"], item["price"]),
                    )

            return _normalize_order(order, order_items)


def _create_mock_order(payload: CreateOrderRequest) -> dict:
    order_items = []
    total_amount = 0

    for item in payload.items:
        product = mock_data.get_product(item.product_id)
        if not product:
            raise ValueError(f"Product {item.product_id} not found")
        if item.quantity > product["stock"]:
            raise ValueError(f"Product {product['name']} is out of stock")

        order_items.append(
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": item.quantity,
                "price": product["price"],
            }
        )
        total_amount += product["price"] * item.quantity

    order = {
        "id": f"OD{1001 + len(mock_data.ORDERS)}",
        "customer_name": payload.customer_name,
        "phone": payload.phone,
        "address": payload.address,
        "status": "Chờ xác nhận",
        "total_amount": total_amount,
        "items": order_items,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_data.ORDERS.append(order)
    return order
