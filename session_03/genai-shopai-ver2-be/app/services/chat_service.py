import os
import re
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.schemas.chat import ChatMode, ChatMessage, ChatRequest, ChatResponse
from app.services import account_service, data_service

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "16"))


def compact_catalog(products: list[dict]) -> str:
    if not products:
        return "- Không có sản phẩm liên quan trực tiếp."

    lines = []
    for product in products:
        variants = ", ".join(product["variants"])
        lines.append(
            f"- {product['id']}: {product['name']} | {product['category']} | "
            f"{format_price(product['price'])} | stock {product['stock']} | variants: {variants} | "
            f"tags: {', '.join(product['tags'])}"
        )
    return "\n".join(lines)


def compact_faqs(faqs: list[dict]) -> str:
    return "\n".join(f"- {faq['question']}: {faq['answer']}" for faq in faqs)


def compact_orders(orders: list[dict]) -> str:
    if not orders:
        return "- Không có mã đơn liên quan trong câu hỏi."

    lines = []
    for order in orders:
        items = ", ".join(
            f"{item['product_name']} x{item['quantity']}" for item in order["items"]
        )
        lines.append(
            f"- {order['id']}: {order['status']}; items: {items}; total: {format_price(order['total_amount'])}"
        )
    return "\n".join(lines)


def normalize(text: str) -> str:
    return text.lower().strip()


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", ".") + "đ"


def find_products(message: str, products: list[dict]):
    normalized = normalize(message)
    matched = []
    for product in products:
        haystack = " ".join(
            [
                product["id"],
                product["name"],
                product["slug"],
                product["category"],
                " ".join(product["tags"]),
            ]
        ).lower()
        if any(token in haystack for token in normalized.split() if len(token) >= 3):
            matched.append(product)
    return matched[:5]


def find_last_product(messages: list[ChatMessage], products: list[dict]):
    for message in reversed(messages):
        for product in products:
            if (
                product["name"].lower() in message.content.lower()
                or product["id"].lower() in message.content.lower()
            ):
                return product
    return None


def find_budget(message: str):
    normalized = normalize(message).replace(".", "").replace(",", "")
    match = re.search(r"duoi\s*(\d+)\s*k|dưới\s*(\d+)\s*k", normalized)
    if match:
        amount = int(next(group for group in match.groups() if group)) * 1000
        return amount

    match = re.search(r"(\d{5,9})\s*(vnd|đ|dong|đồng)?", normalized)
    if match:
        return int(match.group(1))

    return None


def find_order_ids(message: str) -> list[str]:
    return [match.upper() for match in re.findall(r"od\d{4,}", normalize(message))]


def pick_relevant_products(
    message: str, history: list[ChatMessage], mode: ChatMode
) -> list[dict]:
    products = data_service.list_products()
    matches = find_products(message, products)
    budget = find_budget(message)

    if budget:
        budget_matches = [
            product
            for product in products
            if product["price"] <= budget
            and (
                not matches
                or product in matches
                or any(
                    keyword
                    in normalize(product["name"] + " " + " ".join(product["tags"]))
                    for keyword in normalize(message).split()
                )
            )
        ]
        matches = (
            budget_matches[:5]
            or [product for product in products if product["price"] <= budget][:5]
        )

    if mode == ChatMode.WITH_CONTEXT:
        last_product = find_last_product(history, products)
        if last_product and last_product not in matches:
            matches = [last_product, *matches]

    return matches[:5]


def pick_relevant_orders(message: str) -> list[dict]:
    orders = []
    for order_id in find_order_ids(message):
        order = data_service.get_order(order_id)
        if order:
            orders.append(order)
    return orders


def build_system_prompt(
    message: str, mode: ChatMode, history: list[ChatMessage]
) -> str:
    products = pick_relevant_products(message, history, mode)
    orders = pick_relevant_orders(message)
    faqs = data_service.list_faqs()

    return f"""
Bạn là AI chăm sóc khách hàng của ShopAI, một sàn thương mại điện tử demo.
Trả lời bằng tiếng Việt, ngắn gọn, thân thiện.
Chỉ dùng dữ liệu liên quan bên dưới để tư vấn. Nếu dữ liệu chưa đủ, hãy hỏi lại một câu rõ ràng.
Nếu gợi ý sản phẩm, gợi ý tối đa 3 sản phẩm phù hợp và nêu giá, tồn kho, phiên bản/màu nếu có.
Không bịa mã đơn, giá, tồn kho hoặc chính sách ngoài dữ liệu.

SẢN PHẨM LIÊN QUAN:
{compact_catalog(products)}

FAQ / CHÍNH SÁCH:
{compact_faqs(faqs)}

ĐƠN HÀNG LIÊN QUAN:
{compact_orders(orders)}
""".strip()


def fallback_reply(message: str, mode: ChatMode, history: list[ChatMessage]) -> str:
    normalized = normalize(message)
    products = data_service.list_products()
    order_match = re.search(r"od\d{4}", normalized)
    if order_match:
        order = data_service.get_order(order_match.group(0).upper())
        if order:
            items = ", ".join(
                f"{item['product_name']} x{item['quantity']}" for item in order["items"]
            )
            return (
                f'Đơn {order["id"]} hiện đang ở trạng thái "{order["status"]}". '
                f"Sản phẩm gồm: {items}. Tổng tiền {format_price(order['total_amount'])}."
            )
        return "Mình chưa tìm thấy mã đơn này trong dữ liệu demo. Bạn kiểm tra lại giúp mình nhé."

    if any(keyword in normalized for keyword in ["giao", "ship", "vận chuyển"]):
        return "Shop giao nội thành 1-2 ngày, tỉnh thành khác 2-5 ngày. Đơn từ 499.000đ được miễn phí vận chuyển tiêu chuẩn."

    if any(keyword in normalized for keyword in ["đổi", "trả", "hoàn"]):
        return "Bạn có thể đổi trả trong 7 ngày nếu sản phẩm lỗi, sai mẫu hoặc còn nguyên tem nhãn."

    if any(keyword in normalized for keyword in ["bảo hành", "bao hanh"]):
        last_product = (
            find_last_product(history, products)
            if mode == ChatMode.WITH_CONTEXT
            else None
        )
        if last_product and last_product["category"] == "Điện tử":
            return f"{last_product['name']} thuộc nhóm điện tử, thời gian bảo hành demo là 6-12 tháng tùy lỗi."
        return "Sản phẩm điện tử được bảo hành 6-12 tháng. Các nhóm thời trang/gia dụng hỗ trợ đổi trả theo chính sách 7 ngày."

    direct_matches = find_products(message, products)
    budget = find_budget(message)

    if budget:
        product_matches = [
            product
            for product in products
            if product["price"] <= budget
            and any(
                keyword in normalize(product["name"] + " " + " ".join(product["tags"]))
                for keyword in normalized.split()
            )
        ]
        if not product_matches:
            product_matches = [
                product for product in products if product["price"] <= budget
            ]
        suggestions = product_matches[:3]
        if suggestions:
            lines = [
                f"- {product['name']}: {format_price(product['price'])}; còn {product['stock']} sản phẩm; màu/phiên bản: {', '.join(product['variants'])}"
                for product in suggestions
            ]
            return "Mình gợi ý vài sản phẩm hợp ngân sách của bạn:\n" + "\n".join(lines)

    if any(
        keyword in normalized
        for keyword in [
            "cái đó",
            "san pham do",
            "sản phẩm đó",
            "màu đen",
            "còn hàng",
            "giá bao nhiêu",
        ]
    ):
        last_product = (
            find_last_product(history, products)
            if mode == ChatMode.WITH_CONTEXT
            else None
        )
        if last_product:
            black_stock = (
                "có màu Đen"
                if "Đen" in last_product["variants"]
                else "không có màu Đen trong dữ liệu demo"
            )
            return (
                f"Bạn đang hỏi {last_product['name']}. Sản phẩm này giá {format_price(last_product['price'])}, "
                f"còn {last_product['stock']} sản phẩm và {black_stock}."
            )
        return "Bạn đang hỏi sản phẩm nào vậy? Bạn gửi tên sản phẩm hoặc mã sản phẩm giúp mình nhé."

    if direct_matches:
        lines = [
            f"- {product['name']}: {format_price(product['price'])}; rating {product['rating']}; còn {product['stock']} sản phẩm"
            for product in direct_matches[:3]
        ]
        return "Mình tìm thấy các sản phẩm liên quan:\n" + "\n".join(lines)

    return "Mình có thể hỗ trợ tìm sản phẩm, tư vấn theo ngân sách, tra mã đơn OD1001/OD1002/OD1003, hoặc giải đáp giao hàng, đổi trả, bảo hành."


class PersistentChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, conversation_id: str, use_context: bool):
        self.conversation_id = conversation_id
        self.use_context = use_context

    @property
    def messages(self) -> list[BaseMessage]:
        if not self.use_context:
            return []

        langchain_messages: list[BaseMessage] = []
        for message in account_service.list_messages(self.conversation_id):
            if message.role == "user":
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                langchain_messages.append(AIMessage(content=message.content))
        return langchain_messages[-MAX_HISTORY_MESSAGES:]

    def add_messages(self, messages: list[BaseMessage]) -> None:
        for message in messages:
            role = "assistant" if isinstance(message, AIMessage) else "user"
            content = str(message.content)
            if content.strip():
                account_service.append_message(
                    self.conversation_id, role, content.strip()
                )

    def clear(self) -> None:
        account_service.clear_messages(self.conversation_id)


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    conversation_id, mode = session_id.split("|", 1)
    return PersistentChatMessageHistory(
        conversation_id, use_context=mode == ChatMode.WITH_CONTEXT.value
    )


def build_llm():
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            return None
        from langchain_groq import ChatGroq

        return ChatGroq(model=GROQ_MODEL, groq_api_key=GROQ_API_KEY, temperature=0.2)

    if not OPENAI_API_KEY:
        return None

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY)


# Code ở đây
llm = build_llm()
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{message}"),
    ]
)
chat_chain = RunnableWithMessageHistory(
    prompt | llm,
    get_session_history,
    input_messages_key="message",
    history_messages_key="history",
)


def make_title(message: str) -> str:
    normalized = " ".join(message.strip().split())
    if len(normalized) <= 52:
        return normalized or "Cuộc trò chuyện mới"
    return normalized[:49].rstrip() + "..."


def ensure_conversation(user_id: str, payload: ChatRequest) -> dict:
    # Code tiếp ở đây
    if payload.conversation_id:
        conversation = account_service.get_conversation(
            user_id, payload.conversation_id
        )
        if not conversation:
            raise ValueError("Không tìm thấy cuộc trò chuyện của tài khoản này")
        if conversation["mode"] != payload.mode.value:
            conversation = (
                account_service.update_conversation(
                    user_id, payload.conversation_id, mode=payload.mode
                )
                or conversation
            )
        return conversation
    return account_service.create_conversation(
        user_id, payload.mode, title=make_title(payload.message)
    )


def call_langchain(
    message: str, mode: ChatMode, history: list[ChatMessage], conversation_id: str
) -> str | None:
    if chat_chain is None:
        return None

    # Code tiếp ở đây
    response = chat_chain.invoke(
        {
            "system_prompt": build_system_prompt(message, mode, history),
            "message": message,
        },
        config={
            "configurable": {
                "session_id": f"{conversation_id}|{mode.value}",
            }
        },
    )
    content = response.content if hasattr(response, "content") else str(response)
    return content.strip()


def save_fallback_turn(conversation_id: str, user_message: str, reply: str) -> None:
    account_service.append_message(conversation_id, "user", user_message)
    account_service.append_message(conversation_id, "assistant", reply)


def handle_chat(payload: ChatRequest, user_id: str) -> ChatResponse:
    # Code ở đây
    conversation = ensure_conversation(user_id, payload)
    conversation_id = conversation["id"]
    history = (
        account_service.list_messages(conversation_id)
        if payload.mode == ChatMode.WITH_CONTEXT
        else []
    )

    try:
        reply = call_langchain(payload.message, payload.mode, history, conversation_id)
    except Exception:
        reply = None

    if not reply:
        reply = fallback_reply(payload.message, payload.mode, history)
        save_fallback_turn(conversation_id, payload.message, reply)

    messages = account_service.list_messages(conversation_id)
    conversation = (
        account_service.get_conversation(user_id, conversation_id) or conversation
    )

    return ChatResponse(
        conversation_id=conversation_id,
        conversation_title=conversation["title"],
        mode=payload.mode,
        reply=reply,
        used_context=payload.mode == ChatMode.WITH_CONTEXT,
        messages=messages,
    )
