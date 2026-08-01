from __future__ import annotations

import json
import os
import uuid
import warnings
from html import escape
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


try:
    from langchain_core._api.deprecation import LangChainDeprecationWarning

    warnings.filterwarnings(
        "ignore",
        category=LangChainDeprecationWarning,
        message=".*RunnableWithMessageHistory.*",
    )
except Exception:
    pass

load_dotenv()

APP_TITLE = "LangChain Chat Lab"
DEFAULT_SYSTEM_PROMPT = (
    "Bạn là trợ lý AI đang dạy LangChain bằng ví dụ ngắn gọn, dễ hiểu. "
    "Khi người dùng hỏi bằng tiếng Việt, hãy trả lời bằng tiếng Việt. "
    "Nếu có lịch sử hội thoại, hãy tận dụng nó để giữ mạch ngữ cảnh."
)
NOTEBOOK_MAP = [
    {
        "notebook": "1_Intro_to_Langchain.ipynb",
        "concepts": "ChatOpenAI, HumanMessage, PromptTemplate, chain cơ bản.",
        "app_section": "Chat Lab và Prompt Template.",
    },
    {
        "notebook": "2_Chatbots_Groq.ipynb",
        "concepts": "ChatGroq, ChatPromptTemplate, MessagesPlaceholder, RunnableWithMessageHistory.",
        "app_section": "Chat có memory theo session_id.",
    },
]


def init_state() -> None:
    if "histories" not in st.session_state:
        st.session_state.histories = {}
    if "session_id" not in st.session_state:
        st.session_state.session_id = "demo-user"
    if "last_provider" not in st.session_state:
        st.session_state.last_provider = None


def get_history(session_id: str) -> InMemoryChatMessageHistory:
    histories: dict[str, InMemoryChatMessageHistory] = st.session_state.histories
    if session_id not in histories:
        histories[session_id] = InMemoryChatMessageHistory()
    return histories[session_id]


def trim_history(session_id: str, max_messages: int) -> None:
    history = get_history(session_id)
    if len(history.messages) > max_messages:
        history.messages = history.messages[-max_messages:]


def message_role(message: BaseMessage) -> str:
    if isinstance(message, HumanMessage):
        return "user"
    if isinstance(message, AIMessage):
        return "assistant"
    return "assistant"


def message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def render_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }
        [data-testid="stSidebar"] {
            background: #f7f9fb;
            border-right: 1px solid #dce3ea;
        }
        .lab-header {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            justify-content: space-between;
            gap: 0.85rem;
            border-bottom: 1px solid #dde5ed;
            padding-bottom: 0.55rem;
            margin-bottom: 0.75rem;
        }
        .lab-title {
            color: #132033;
            font-size: 1.28rem;
            font-weight: 720;
            line-height: 1.2;
        }
        .lab-subtitle {
            color: #536273;
            font-size: 0.84rem;
            line-height: 1.35;
            margin-top: 0.12rem;
        }
        .status-pill {
            border: 1px solid #cfd9e3;
            border-radius: 999px;
            color: #24465d;
            background: #ffffff;
            font-size: 0.76rem;
            padding: 0.28rem 0.58rem;
            white-space: nowrap;
        }
        @media (max-width: 760px) {
            .block-container {
                padding-top: 2rem;
            }
            .lab-header {
                grid-template-columns: 1fr;
                gap: 0.45rem;
            }
            .status-pill {
                width: fit-content;
            }
        }
        .memory-row {
            border: 1px solid #dce4ec;
            border-radius: 8px;
            padding: 0.7rem 0.8rem;
            margin-bottom: 0.55rem;
            background: #ffffff;
        }
        .memory-role {
            color: #4b5d70;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
        }
        .memory-text {
            color: #1b2635;
            margin-top: 0.25rem;
            white-space: pre-wrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(provider: str, session_id: str, context_enabled: bool) -> None:
    context_label = "Memory bật" if context_enabled else "Memory tắt"
    st.markdown(
        f"""
        <div class="lab-header">
            <div>
                <div class="lab-title">{APP_TITLE}</div>
                <div class="lab-subtitle">Một app nhỏ để thử ChatPromptTemplate, MessagesPlaceholder và lịch sử hội thoại theo session.</div>
            </div>
            <div class="status-pill">{provider} · {session_id} · {context_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def provider_is_ready(provider: str) -> bool:
    if provider == "OpenAI":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "Groq":
        return bool(os.getenv("GROQ_API_KEY"))
    return True


def default_provider() -> str:
    env_provider = os.getenv("LANGCHAIN_APP_PROVIDER", "Demo").strip().lower()
    provider_map = {"demo": "Demo", "openai": "OpenAI", "groq": "Groq"}
    return provider_map.get(env_provider, "Demo")


def default_model(provider: str) -> str:
    if provider == "OpenAI":
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if provider == "Groq":
        return os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    return "demo-langchain"


def demo_reply(prompt_value: Any) -> AIMessage:
    messages = prompt_value.to_messages()
    user_messages = [
        message_text(msg.content) for msg in messages if isinstance(msg, HumanMessage)
    ]
    latest = user_messages[-1] if user_messages else ""
    remembered = max(len(user_messages) - 1, 0)
    if remembered:
        content = (
            f'Demo mode: mình nhận câu mới là: "{latest}".\n\n'
            f"Trong prompt hiện tại có {remembered} lượt người dùng trước đó, nên đây là ví dụ memory đang được truyền qua `MessagesPlaceholder`."
        )
    else:
        content = (
            f'Demo mode: mình nhận câu này độc lập: "{latest}".\n\n'
            "Nếu bật memory và hỏi tiếp cùng `session_id`, app sẽ đưa lịch sử vào prompt cho lượt sau."
        )
    return AIMessage(content=content)


def build_model(provider: str, model_name: str, temperature: float):
    if provider == "OpenAI":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Thiếu OPENAI_API_KEY trong file .env.")
        return ChatOpenAI(model=model_name, temperature=temperature)
    if provider == "Groq":
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("Thiếu GROQ_API_KEY trong file .env.")
        return ChatGroq(model=model_name, temperature=temperature)
    return RunnableLambda(demo_reply)


def build_chain(
    provider: str,
    model_name: str,
    temperature: float,
    system_prompt: str,
    context_enabled: bool = True,
):
    # 1. Model
    model = build_model(provider, model_name, temperature)

    # 2. Prompt template (sẽ được thiết lập khi context_enabled = True)
    if context_enabled:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )
        chain = prompt | model
        return RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    # 3. Memory tắt: prompt không có MessagesPlaceholder, model chỉ thấy câu hỏi
    # hiện tại -> đúng hành vi "không nhớ ngữ cảnh" của buổi 1.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    return prompt | model


def invoke_chat(
    user_input: str,
    provider: str,
    model_name: str,
    temperature: float,
    system_prompt: str,
    context_enabled: bool,
    session_id: str,
) -> str:
    # 1. khởi tạo chain
    chain = build_chain(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        system_prompt=system_prompt,
        context_enabled=context_enabled,
    )

    # 2. Có memory: RunnableWithMessageHistory tự đọc/ghi lịch sử theo session_id
    if context_enabled:
        response = chain.invoke(
            {"input": user_input},
            config={
                "configurable": {
                    "session_id": session_id,
                }
            },
        )
        return message_text(response.content)

    # 3. Không memory: model không thấy lịch sử, nhưng vẫn ghi lại để tab Chat và
    # Memory Viewer hiển thị được cuộc hội thoại sau mỗi lần rerun.
    response = chain.invoke({"input": user_input})
    answer = message_text(response.content)

    history = get_history(session_id)
    history.add_user_message(user_input)
    history.add_ai_message(answer)
    return answer


def invoke_template(
    provider: str,
    model_name: str,
    temperature: float,
    source_lang: str,
    target_lang: str,
    tone: str,
    text: str,
) -> str:
    model = build_model(provider, model_name, temperature)

    # Prompt có 4 biến -> minh hoạ ChatPromptTemplate như một hàm nhận tham số,
    # thay vì nối chuỗi bằng f-string.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Bạn là một dịch giả chuyên nghiệp. Hãy dịch nội dung của người dùng "
                "từ {source_lang} sang {target_lang} với giọng văn {tone}. "
                "Chỉ trả về bản dịch, không thêm giải thích hay ghi chú.",
            ),
            ("human", "{text}"),
        ]
    )

    # StrOutputParser để chain trả thẳng str thay vì AIMessage.
    chain = prompt | model | StrOutputParser()

    return chain.invoke(
        {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "tone": tone,
            "text": text,
        }
    )


def render_sidebar() -> dict[str, Any]:
    st.sidebar.title("Cấu hình")

    provider_options = ["Demo", "OpenAI", "Groq"]
    provider = st.sidebar.selectbox(
        "Provider",
        provider_options,
        index=provider_options.index(default_provider()),
    )

    if st.session_state.last_provider != provider:
        st.session_state.model_name = default_model(provider)
        st.session_state.last_provider = provider

    model_name = st.sidebar.text_input(
        "Model",
        key="model_name",
        disabled=provider == "Demo",
    )
    temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    context_enabled = st.sidebar.toggle("Dùng memory theo session", value=True)
    max_turns = st.sidebar.slider("Giữ tối đa bao nhiêu lượt gần nhất", 2, 20, 8)

    st.sidebar.divider()
    session_id = st.sidebar.text_input("Session ID", value=st.session_state.session_id)
    st.session_state.session_id = session_id.strip() or "demo-user"

    cols = st.sidebar.columns(2)
    if cols[0].button("Session mới", use_container_width=True):
        st.session_state.session_id = f"user-{uuid.uuid4().hex[:6]}"
        st.rerun()
    if cols[1].button("Xóa session", use_container_width=True):
        st.session_state.histories.pop(st.session_state.session_id, None)
        st.rerun()

    if st.sidebar.button("Xóa toàn bộ memory", use_container_width=True):
        st.session_state.histories = {}
        st.rerun()

    st.sidebar.divider()
    system_prompt = st.sidebar.text_area(
        "System prompt",
        value=DEFAULT_SYSTEM_PROMPT,
        height=150,
    )

    if not provider_is_ready(provider):
        missing = "OPENAI_API_KEY" if provider == "OpenAI" else "GROQ_API_KEY"
        st.sidebar.warning(f"Thiếu {missing}. Chọn Demo hoặc thêm key vào .env.")

    return {
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
        "context_enabled": context_enabled,
        "max_messages": max_turns * 2,
        "session_id": st.session_state.session_id,
        "system_prompt": system_prompt,
    }


def render_chat_tab(config: dict[str, Any]) -> None:
    history = get_history(config["session_id"])

    for message in history.messages:
        with st.chat_message(message_role(message)):
            st.markdown(message_text(message.content))

    user_input = st.chat_input("Nhập câu hỏi để thử memory LangChain...")
    if not user_input:
        return

    if not provider_is_ready(config["provider"]):
        st.error("Provider hiện tại chưa có API key trong .env.")
        return

    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        with st.chat_message("assistant"):
            with st.spinner("LangChain đang chạy chain..."):
                answer = invoke_chat(
                    user_input=user_input,
                    provider=config["provider"],
                    model_name=config["model_name"],
                    temperature=config["temperature"],
                    system_prompt=config["system_prompt"],
                    context_enabled=config["context_enabled"],
                    session_id=config["session_id"],
                )
                trim_history(config["session_id"], config["max_messages"])
                st.markdown(answer)
    except Exception as exc:
        st.error(f"Không gọi được model: {exc}")


def render_template_tab(config: dict[str, Any]) -> None:
    with st.form("template-form"):
        col_a, col_b = st.columns(2)
        source_lang = col_a.text_input("Ngôn ngữ nguồn", value="Tiếng Việt")
        target_lang = col_b.text_input("Ngôn ngữ đích", value="English")
        tone = st.selectbox(
            "Giọng văn",
            ["Tự nhiên", "Chuyên nghiệp", "Thân thiện", "Ngắn gọn"],
        )
        text = st.text_area(
            "Nội dung cần dịch",
            value="LangChain giúp mình ghép prompt, model và memory thành một chain dễ quản lý.",
            height=140,
        )
        submitted = st.form_submit_button(
            "Chạy prompt template", use_container_width=True
        )

    if not submitted:
        return

    if not provider_is_ready(config["provider"]):
        st.error("Provider hiện tại chưa có API key trong .env.")
        return

    try:
        with st.spinner("Đang invoke prompt template..."):
            result = invoke_template(
                provider=config["provider"],
                model_name=config["model_name"],
                temperature=config["temperature"],
                source_lang=source_lang,
                target_lang=target_lang,
                tone=tone,
                text=text,
            )
        st.markdown("**Kết quả**")
        st.markdown(result)
    except Exception as exc:
        st.error(f"Không gọi được model: {exc}")


def render_memory_tab(config: dict[str, Any]) -> None:
    histories: dict[str, InMemoryChatMessageHistory] = st.session_state.histories
    session_ids = sorted(histories.keys()) or [config["session_id"]]
    selected = st.selectbox(
        "Chọn session",
        session_ids,
        index=session_ids.index(config["session_id"])
        if config["session_id"] in session_ids
        else 0,
    )
    history = get_history(selected)

    if not history.messages:
        st.info("Session này chưa có message nào.")
    else:
        for message in history.messages:
            role = "Human" if isinstance(message, HumanMessage) else "AI"
            safe_content = escape(message_text(message.content))
            st.markdown(
                f"""
                <div class="memory-row">
                    <div class="memory-role">{role}</div>
                    <div class="memory-text">{safe_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    export_rows = [
        {"role": message_role(message), "content": message_text(message.content)}
        for message in history.messages
    ]
    st.download_button(
        "Tải memory JSON",
        data=json.dumps(export_rows, ensure_ascii=False, indent=2),
        file_name=f"{selected}-memory.json",
        mime="application/json",
        use_container_width=True,
        disabled=not export_rows,
    )


def render_notebook_tab() -> None:
    for item in NOTEBOOK_MAP:
        with st.expander(item["notebook"], expanded=True):
            st.markdown(f"**Kiến thức:** {item['concepts']}")
            st.markdown(f"**Được đưa vào app:** {item['app_section']}")

    st.code(
        """
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])

chain = prompt | model
chatbot = RunnableWithMessageHistory(
    chain,
    get_history,
    input_messages_key="input",
    history_messages_key="history",
)
        """.strip(),
        language="python",
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="LC", layout="wide")
    init_state()
    render_css()
    config = render_sidebar()
    render_header(config["provider"], config["session_id"], config["context_enabled"])

    chat_tab, template_tab, memory_tab, notebook_tab = st.tabs(
        ["Chat Lab", "Prompt Template", "Memory Viewer", "Notebook Map"]
    )
    with chat_tab:
        render_chat_tab(config)
    with template_tab:
        render_template_tab(config)
    with memory_tab:
        render_memory_tab(config)
    with notebook_tab:
        render_notebook_tab()


if __name__ == "__main__":
    main()
