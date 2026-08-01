# Buổi 2 — LangChain, Groq và memory theo `session_id`

Ngày học: 07/07/2026

> Slide `docs/29-06-2026-01-28-31-buoi-2-3-langchain-groq.pdf` bao trùm cả buổi 2 và buổi 3.

## Mục tiêu

Buổi 1 gọi thẳng SDK của OpenAI. Buổi 2 chuyển sang **LangChain** — một lớp trừu tượng đứng trên nhiều provider — và giải quyết lại bài toán ngữ cảnh, nhưng lần này bằng cơ chế có sẵn thay vì tự quản lý list `messages`.

Ba file minh hoạ:

1. `intro_to_langchain.ipynb` — `ChatOpenAI`, message tuple, `ChatPromptTemplate`, chain bằng toán tử `|`.
2. `intro_to_groq.ipynb` — `ChatGroq`, `RunnableWithMessageHistory`, nhiều session song song.
3. `streamlit_app.py` — gộp tất cả thành app "LangChain Chat Lab" có UI.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. LangChain chuẩn hoá interface giữa các provider

```python
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

llm   = ChatOpenAI(model="gpt-5-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
model = ChatGroq(model="openai/gpt-oss-20b", groq_api_key=os.getenv("GROQ_API_KEY"))
```

Hai class khác nhau nhưng cùng interface `.invoke()`, cùng nhận/trả `BaseMessage`. Đây là lý do `streamlit_app.py` đổi được provider bằng một dropdown mà phần chain phía dưới không đổi dòng nào:

```python
def build_model(provider, model_name, temperature):
    if provider == "OpenAI": return ChatOpenAI(model=model_name, temperature=temperature)
    if provider == "Groq":   return ChatGroq(model=model_name, temperature=temperature)
    return RunnableLambda(demo_reply)     # chế độ Demo, không tốn API call
```

**Groq** ở đây là một inference provider (chạy các model open-weight như `openai/gpt-oss-20b`, `qwen/qwen3-32b`), dùng biến môi trường riêng `GROQ_API_KEY`.

`temperature` là tham số mới so với buổi 1: 0 = ổn định/lặp lại được, càng cao càng ngẫu nhiên.

### 2. Ba cách viết message trong LangChain

| Cách viết | Ví dụ |
| --- | --- |
| Object | `SystemMessage(...)`, `HumanMessage(content="Python là gì?")`, `AIMessage(...)` |
| Tuple | `("system", "..."), ("human", "{input}")` |
| Dict | `{"role": "user", "content": "..."}` (giống buổi 1) |

Kết quả `invoke` trả về một `AIMessage` — không chỉ có `.content` mà còn `.response_metadata` (token usage, model name, finish reason) và `.tool_calls`. `token_usage` là chỗ để theo dõi chi phí.

### 3. `ChatPromptTemplate` — prompt có biến

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "Bạn là một trợ lý AI, bạn sẽ trả lời bằng {language}"),
    ("human", "{input}"),
])
chain = prompt | llm
chain.invoke({"language": "Bồ Đào Nha", "input": "Python là gì?"})
```

Prompt trở thành **template có tham số** thay vì chuỗi cứng. Giá trị được truyền lúc `invoke` dưới dạng dict.

### 4. LCEL — ghép component bằng toán tử `|`

`prompt | model` tạo ra một **chain**: output của bước trước là input của bước sau. Cả chain vẫn là một Runnable, tức là vẫn có `.invoke()`, `.batch()`, `.stream()`. Đây là ý tưởng trung tâm của LangChain Expression Language.

### 5. Memory theo `session_id` — điểm mấu chốt của buổi

Buổi 1 phải tự append vào list và tự gửi lại. LangChain đóng gói việc đó:

```python
store = {}   # dict: session_id -> lịch sử hội thoại

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

with_message_history = RunnableWithMessageHistory(model, get_session_history)
```

Khi invoke, `session_id` được truyền qua `config`:

```python
response = with_message_history.invoke(
    messages,
    config={"configurable": {"session_id": "session_1"}},
)
```

`RunnableWithMessageHistory` tự động: đọc lịch sử của session → chèn vào prompt → gọi model → ghi cả câu hỏi lẫn câu trả lời trở lại lịch sử.

**Thí nghiệm trong notebook chứng minh sự cô lập giữa các session:**

| Session | Câu hỏi | Kết quả |
| --- | --- | --- |
| `session_1` | "Xin chào, tôi tên là An, tôi là một giảng viên" | Bot chào "An" |
| `session_2` | "Tôi là ai, và tôi làm gì?" | Bot **không biết** — session_2 có lịch sử rỗng |

Đây chính là cơ chế cho phép một server phục vụ nhiều người dùng cùng lúc mà không lẫn hội thoại.

### 6. `MessagesPlaceholder` — chỗ để nhét lịch sử vào prompt

Khi chain có prompt template, phải chỉ rõ lịch sử được chèn vào đâu và input đọc từ key nào:

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),   # lịch sử đổ vào đây
    ("human", "{input}"),
])

chain = prompt | model
chatbot = RunnableWithMessageHistory(
    chain,
    get_history,
    input_messages_key="input",       # key chứa câu hỏi mới
    history_messages_key="history",   # tên placeholder ở trên
)
```

Thiếu `input_messages_key` / `history_messages_key` thì LangChain không biết field nào là gì khi input là dict nhiều key.

### 7. Cắt bớt lịch sử để khống chế token

```python
def trim_history(session_id: str, max_messages: int) -> None:
    history = get_history(session_id)
    if len(history.messages) > max_messages:
        history.messages = history.messages[-max_messages:]
```

Chỉ giữ N message gần nhất. Trong app, slider "Giữ tối đa bao nhiêu lượt gần nhất" chính là tham số này (`max_turns * 2` vì mỗi lượt có 1 human + 1 AI). Đây là câu trả lời trực tiếp cho vấn đề "hội thoại càng dài càng đắt" đã nêu ở buổi 1.

### 8. Kỹ thuật Streamlit bổ sung so với buổi 1

| Kỹ thuật | Mục đích |
| --- | --- |
| `st.sidebar` + `selectbox` / `slider` / `toggle` | Panel cấu hình runtime (provider, model, temperature, bật/tắt memory) |
| `st.tabs([...])` | Chia app thành Chat Lab / Prompt Template / Memory Viewer / Notebook Map |
| `st.form` + `form_submit_button` | Gom nhiều input, chỉ chạy khi bấm submit (tránh rerun mỗi lần gõ) |
| `st.spinner` | Báo hiệu đang chờ model |
| `st.session_state.histories` | Dict lưu **nhiều** `InMemoryChatMessageHistory`, key là `session_id` |
| `st.download_button` | Xuất memory ra JSON |
| `RunnableLambda(demo_reply)` | Chế độ Demo — chạy thử UI/memory mà không cần API key |

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `intro_to_langchain.ipynb` | `ChatOpenAI`, message tuple, `ChatPromptTemplate`, chain `prompt \| llm` |
| `intro_to_groq.ipynb` | `ChatGroq`, `RunnableWithMessageHistory`, demo nhiều `session_id` |
| `streamlit_app.py` | App "LangChain Chat Lab" 4 tab, đổi provider runtime, memory viewer |
| `requirements.txt` | `langchain`, `langchain-core`, `langchain-openai`, `langchain-groq`, `langchain-community`, `streamlit`, `python-dotenv`, `jupyter` |
| `docs/*.pdf` | Slide buổi 2–3 (LangChain + Groq) |
| `docs/teacher_codes/` | Notebook gốc của giảng viên |
| `docs/resources/Chat with Session ID` | Bản đề bài của `streamlit_app.py` (các hàm để trống) |

## Cách chạy

```bash
pip install -r requirements.txt

# .env
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk_...
# LANGCHAIN_APP_PROVIDER=Demo      # tùy chọn: Demo | OpenAI | Groq

streamlit run streamlit_app.py
```

Không có API key vẫn chạy được app ở chế độ **Demo** để quan sát cơ chế memory.

## Phần còn dang dở

- `invoke_template()` (`streamlit_app.py:308`) vẫn là `return` rỗng → tab **Prompt Template** chưa hoạt động. Cần dựng một `ChatPromptTemplate` nhận `source_lang` / `target_lang` / `tone` / `text` rồi `prompt | model | StrOutputParser()`, đúng kỹ thuật ở mục 3–4.
- `build_chain()` (`streamlit_app.py:249`) mới xử lý nhánh `context_enabled=True`; khi tắt toggle memory ở sidebar, hàm trả về `None` và `invoke_chat` sẽ lỗi.
