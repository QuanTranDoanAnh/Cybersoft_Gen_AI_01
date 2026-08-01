import os
import sqlite3
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from sqlalchemy import URL, create_engine


load_dotenv(Path(__file__).with_name(".env"))

LOCAL_DB = "USE_LOCAL_DB"
MYSQL_DB = "USE_MYSQL"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

st.set_page_config(page_title="Chat with SQL DB", page_icon="🦜")
st.markdown(
    """
    <style>
    .block-container {
        max-width: 980px;
        width: 100%;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stAppViewContainer"] h1 {
        font-size: clamp(1.8rem, 3vw, 2.5rem);
        line-height: 1.12;
        overflow-wrap: anywhere;
    }
    [data-testid="stAppViewContainer"] p,
    [data-testid="stChatMessage"] {
        overflow-wrap: anywhere;
    }
    [data-testid="stChatMessage"] {
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 16px;
        padding: 0.35rem 0.75rem;
        margin-bottom: 0.75rem;
    }
    [data-testid="stChatMessage"] pre {
        border-radius: 10px;
    }
    [data-testid="stChatMessage"] table {
        width: 100%;
        display: block;
        overflow-x: auto;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🦜 Chat with SQL DB")
st.caption("Đặt câu hỏi bằng ngôn ngữ tự nhiên và nhận kết quả trực tiếp từ cơ sở dữ liệu.")

database_option = st.sidebar.radio(
    "Choose a database",
    ("SQLite (student.db)", "MySQL"),
)
db_type = LOCAL_DB if database_option.startswith("SQLite") else MYSQL_DB

mysql_host = mysql_user = mysql_password = mysql_database = None
if db_type == MYSQL_DB:
    mysql_host = st.sidebar.text_input("MySQL host")
    mysql_user = st.sidebar.text_input("MySQL user")
    mysql_password = st.sidebar.text_input("MySQL password", type="password")
    mysql_database = st.sidebar.text_input("MySQL database")

api_key = st.sidebar.text_input(
    "OpenAI API key",
    value=os.getenv("OPENAI_API_KEY", ""),
    type="password",
)
model_name = st.sidebar.text_input("OpenAI model", value=DEFAULT_MODEL)


@st.cache_resource(ttl="2h")
def configure_db(
    db_type: str,
    host: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> SQLDatabase:
    if db_type == LOCAL_DB:
        db_path = Path(__file__).with_name("student.db").resolve()

        def connect_read_only() -> sqlite3.Connection:
            return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        engine = create_engine("sqlite://", creator=connect_read_only)
        return SQLDatabase(engine)

    if not all((host, user, password, database)):
        raise ValueError("Please provide all MySQL connection details.")

    url = URL.create(
        "mysql+mysqlconnector",
        username=user,
        password=password,
        host=host,
        database=database,
    )
    return SQLDatabase(create_engine(url, pool_pre_ping=True))


if not api_key:
    st.info("Add your OpenAI API key in the sidebar or in the .env file.")
    st.stop()

if not model_name.strip():
    st.info("Enter an OpenAI model name.")
    st.stop()

try:
    db = configure_db(
        db_type,
        mysql_host,
        mysql_user,
        mysql_password,
        mysql_database,
    )
except Exception as exc:
    st.error(f"Could not connect to the database: {exc}")
    st.stop()

# SQL Database Toolkits
llm = ChatOpenAI(model=model_name.strip(), api_key=api_key)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

system_prompt = f"""
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {db.dialect} query to
run, inspect its results, and answer the question. Unless the user specifies a
different number, limit the query to at most 10 rows.

Select only relevant columns. Always inspect the available tables first, then
inspect the schema of the relevant tables. Double-check every query before
execution; if a query fails, correct it and retry.

Never execute data-changing or schema-changing statements such as INSERT,
UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, or TRUNCATE.

Format the final answer as clean Markdown in the same language as the user:
- Start with `### Kết quả` for Vietnamese or `### Result` for English.
- State the direct answer first and bold important values.
- When returning multiple records, use a Markdown table with concise column names.
- Add a short `#### SQL đã sử dụng` or `#### SQL used` section containing the
  final SQL query in a fenced `sql` code block.
- If no rows match, say so clearly instead of displaying an empty table.
- Do not expose internal reasoning, tool names, or raw Python tuple output.
"""

# Create Agent
agent = create_agent(
    llm, 
    tools=tools, 
    system_prompt=system_prompt
)

if "messages" not in st.session_state or st.sidebar.button("Clear chat history"):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "### Xin chào! 👋\n\n"
                "Bạn muốn tìm hiểu thông tin gì trong cơ sở dữ liệu?"
            ),
        }
    ]


def content_to_markdown(content: object) -> str:
    """Convert OpenAI/LangChain text content into displayable Markdown."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        if text_parts:
            return "\n\n".join(text_parts)

    return str(content)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_query = st.chat_input("Ask a question about the database")
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Đang phân tích dữ liệu..."):
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": user_query}]},
                )
            response = content_to_markdown(result["messages"][-1].content)
        except Exception as exc:
            response = f"Unable to answer the question: {exc}"
            st.error(response)
        else:
            st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )