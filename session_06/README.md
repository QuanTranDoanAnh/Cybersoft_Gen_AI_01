# Buổi 6 — SQL Agent: cho LLM truy vấn cơ sở dữ liệu

Ngày học: 20/07/2026

## Mục tiêu

Buổi 5 dạy cách tự viết tool bằng `@tool`. Buổi 6 dùng một **toolkit dựng sẵn**: `SQLDatabaseToolkit` — bộ tool cho phép agent tự khám phá schema, tự viết SQL, tự chạy và tự sửa khi lỗi.

Kết quả là một chatbot **Text-to-SQL**: người dùng hỏi bằng tiếng Việt/tiếng Anh, agent trả lời bằng số liệu lấy trực tiếp từ database.

File minh hoạ: `docs/[Resources] Agent_SQL` → bản đã làm là `Agent_SQL.ipynb`; `docs/SQL Agent Streamlit` → bản đã làm là `app.py`.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. `SQLDatabase` — bọc database thành object LangChain hiểu được

```python
from langchain_community.utilities import SQLDatabase

db = SQLDatabase.from_uri("sqlite:///Chinook.db")

print(f"Database: {db.dialect}")                  # sqlite
print(f"Tables: {db.get_usable_table_names()}")   # ['Album', 'Artist', 'Customer', ...]
db.run("SELECT * FROM Artist LIMIT 5;")           # [(1, 'AC/DC'), (2, 'Accept'), ...]
```

`SQLDatabase` xây trên **SQLAlchemy**, nên chỉ cần đổi connection string là chuyển được SQLite → MySQL → Postgres. Ba method quan trọng:

| Method | Vai trò |
| --- | --- |
| `.dialect` | Tên phương ngữ SQL — nhét vào prompt để model sinh đúng cú pháp |
| `.get_usable_table_names()` | Danh sách bảng — agent dùng để biết có gì mà hỏi |
| `.run(query)` | Thực thi câu SQL |

### 2. `SQLDatabaseToolkit` — 4 tool đóng gói sẵn

```python
from langchain_community.agent_toolkits import SQLDatabaseToolkit

toolkit = SQLDatabaseToolkit(db=db, llm=model)
tools = toolkit.get_tools()
```

Bốn tool nhận được, thiết kế đúng theo quy trình một người phân tích dữ liệu sẽ làm:

| Tool | Vai trò |
| --- | --- |
| `sql_db_list_tables` | Liệt kê các bảng có trong DB |
| `sql_db_schema` | Lấy `CREATE TABLE` + vài dòng dữ liệu mẫu của bảng chỉ định |
| `sql_db_query_checker` | **Nhờ LLM soát lại câu SQL trước khi chạy** |
| `sql_db_query` | Thực thi câu SQL, trả về kết quả |

Điểm đáng chú ý: `SQLDatabaseToolkit` nhận cả `db` **và** `llm`, vì `sql_db_query_checker` bên trong là một `LLMChain` riêng — prompt của nó liệt kê các lỗi SQL kinh điển (`NOT IN` với `NULL`, `UNION` thay vì `UNION ALL`, `BETWEEN` cho khoảng mở, sai kiểu dữ liệu, join sai cột…) và yêu cầu model viết lại nếu phát hiện.

Đây là mẫu hình quan trọng: **dùng LLM để kiểm tra output của chính LLM** trước khi thực thi một hành động có rủi ro.

### 3. Tại sao phải cho agent xem schema thay vì nhét hết vào prompt

`sql_db_schema` chỉ trả về schema của **những bảng agent chọn**. Với database vài chục bảng, nhét toàn bộ schema vào system prompt sẽ tốn rất nhiều token mỗi lượt. Cho agent tự tra từng bước tiết kiệm hơn nhiều — và đó chính là lý do system prompt bắt buộc thứ tự:

> To start you should ALWAYS look at the tables in the database to see what you can query. Do NOT skip this step. Then you should query the schema of the most relevant tables.

### 4. System prompt cho SQL agent — 5 ràng buộc cốt lõi

```python
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.
...
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
""".format(dialect=db.dialect, top_k=5)
```

| Ràng buộc | Lý do |
| --- | --- |
| `{dialect}` nhét động vào prompt | Cú pháp SQLite ≠ MySQL ≠ Postgres |
| `LIMIT {top_k}` | Tránh kéo về hàng triệu dòng làm nổ context window |
| "Never query for all the columns" | Chỉ lấy cột cần thiết, giảm token |
| "MUST double check your query" | Bắt buộc đi qua `sql_db_query_checker` |
| **"DO NOT make any DML statements"** | Chặn ghi/xoá dữ liệu |

### 5. `create_agent()` — vòng lặp agent viết sẵn

```python
from langchain.agents import create_agent

agent = create_agent(model, tools, system_prompt=system_prompt)
```

Buổi 5 phải tự viết vòng lặp (`for _ in range(4)`, tự `.invoke()` tool, tự append `ToolMessage`). `create_agent()` đóng gói toàn bộ vòng lặp đó. Đây cũng chính là hàm đã gặp ở buổi 4 với `response_format=` — cùng một API, khác tham số.

### 6. `agent.stream()` — quan sát agent suy nghĩ từng bước

```python
for step in agent.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()
```

Với câu hỏi *"Which genre on average has the longest tracks?"*, agent chạy đúng 4 bước:

```
Human      →  Which genre on average has the longest tracks?
AI         →  gọi sql_db_list_tables
Tool       →  Album, Artist, Customer, Employee, Genre, Invoice, ..., Track
AI         →  gọi sql_db_schema(table_names="Genre, Track")
Tool       →  CREATE TABLE "Genre" (...) / CREATE TABLE "Track" (... Milliseconds INTEGER ...)
AI         →  gọi sql_db_query_checker(query="SELECT g.Name, AVG(t.Milliseconds) ...")
Tool       →  (trả lại câu SQL đã soát)
AI         →  gọi sql_db_query(query=...)
Tool       →  [('Sci Fi & Fantasy', 2911783.03, 26), ('Science Fiction', ...), ...]
AI         →  Genre with the longest average tracks: "Sci Fi & Fantasy" ≈ 48 phút 31s
```

Toàn bộ chuỗi này agent tự quyết định — không ai viết sẵn "hãy list bảng rồi xem schema rồi query". `stream_mode="values"` trả về **toàn bộ state** sau mỗi bước, `.pretty_print()` in ra dạng dễ đọc. Đây là công cụ debug agent quan trọng nhất của buổi.

Cũng lưu ý agent **tự chọn** `Milliseconds` sau khi đọc schema, và tự biết phải `JOIN Genre` với `Track` qua `GenreId` — thông tin nó chỉ có được từ bước `sql_db_schema`.

### 7. Chặn ghi dữ liệu ở tầng kết nối, không chỉ ở prompt

System prompt bảo "đừng INSERT/DELETE" — nhưng prompt chỉ là lời khuyên, model có thể bỏ qua. `app.py` chặn ở tầng thấp hơn:

```python
def connect_read_only() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

engine = create_engine("sqlite://", creator=connect_read_only)
return SQLDatabase(engine)
```

`mode=ro` trong SQLite URI mở file ở chế độ **chỉ đọc**. Dù model có sinh ra `DROP TABLE` thì SQLite cũng từ chối.

Nguyên tắc: **phòng thủ nhiều lớp**. Prompt là lớp một, quyền của connection là lớp hai — và lớp hai mới là lớp không thể vượt qua. Với MySQL, tương đương là tạo user chỉ có quyền `SELECT`.

### 8. Đổi database runtime bằng SQLAlchemy `URL.create`

```python
url = URL.create(
    "mysql+mysqlconnector",
    username=user, password=password, host=host, database=database,
)
return SQLDatabase(create_engine(url, pool_pre_ping=True))
```

`URL.create()` tự escape ký tự đặc biệt trong password — an toàn hơn nối chuỗi tay. `pool_pre_ping=True` kiểm tra connection còn sống trước khi dùng, tránh lỗi "MySQL server has gone away" với connection nhàn rỗi lâu.

### 9. `@st.cache_resource` vs `@st.cache_data`

```python
@st.cache_resource(ttl="2h")
def configure_db(...) -> SQLDatabase:
```

Buổi 3 dùng `@st.cache_data` cho **dữ liệu** (transcript — copy được, serialize được). Ở đây là `@st.cache_resource` cho **tài nguyên dùng chung** như database connection, model — những thứ không nên copy mỗi lần rerun mà phải dùng chung một instance. `ttl="2h"` để connection cũ được tạo lại định kỳ.

### 10. Ép định dạng output ngay trong system prompt

`app.py` bổ sung một khối chỉ dẫn trình bày mà notebook không có:

```
- Start with `### Kết quả` for Vietnamese or `### Result` for English.
- When returning multiple records, use a Markdown table with concise column names.
- Add a short `#### SQL đã sử dụng` section containing the final SQL query in a fenced `sql` code block.
- If no rows match, say so clearly instead of displaying an empty table.
- Do not expose internal reasoning, tool names, or raw Python tuple output.
```

Ba điểm đáng học:

- **Trả lời cùng ngôn ngữ với người hỏi** — chỉ dẫn thay vì hardcode.
- **Hiện lại câu SQL đã dùng** — người dùng kiểm chứng được kết quả, cùng tinh thần với `ToolTrace` ở buổi 5.
- **Giấu chi tiết nội bộ** — tuple Python thô (`[('Sci Fi & Fantasy', 2911783.03, 26)]`) không phải thứ người dùng cuối nên thấy.

### 11. `content_to_markdown()` — `.content` không phải lúc nào cũng là string

```python
def content_to_markdown(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # content có thể là list các block {"type": "text", "text": "..."}
        ...
```

Với model đời mới, `AIMessage.content` có thể là **list content block** thay vì string thuần (do reasoning/multimodal). Viết `st.markdown(result["messages"][-1].content)` trực tiếp sẽ ra chuỗi `[{'type': 'text', ...}]` xấu xí. Hàm này chuẩn hoá về string.

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `Agent_SQL.ipynb` | Bản đã làm — `SQLDatabase`, toolkit, `create_agent`, `agent.stream()` trên Chinook.db |
| `app.py` | Chatbot Streamlit "Chat with SQL DB", chọn SQLite/MySQL, SQLite mở read-only |
| `chinhook_db.py` | Script tải `Chinook.db` (DB mẫu về cửa hàng nhạc) từ Google Storage |
| `student.db` | DB SQLite nhỏ dùng cho `app.py` |
| `requirements.txt` | `streamlit`, `langchain`, `langchain-community`, `langchain-openai`, `SQLAlchemy`, `mysql-connector-python` |
| `docs/` | Bản đề bài của notebook và app (các ô để trống), cùng đề bài project |

## Project đi kèm (theo `docs/docker-compose.yml`)

`docs/docker-compose.yml` mô tả một stack Postgres + backend + frontend với `POSTGRES_DB: powerbi_copilot` và mount `./tvshows:/data/tvshows:ro` (dữ liệu nằm trong `docs/tvshows.zip`, ~8 MB). Tức là bài tập của buổi là dựng một **BI copilot** hỏi đáp bằng ngôn ngữ tự nhiên trên bộ dữ liệu TV shows — áp dụng đúng SQL agent vừa học, nhưng trên Postgres và có UI thật.

Code backend/frontend chưa có trong repo; hiện mới có notebook, `app.py` và tài nguyên đề bài.

## Cách chạy

```bash
pip install -r requirements.txt

# .env
# OPENAI_API_KEY=sk-...

python chinhook_db.py                # tải Chinook.db về (chỉ cần cho notebook)
jupyter notebook Agent_SQL.ipynb

streamlit run app.py                 # chatbot trên student.db
```

## Ghi chú

`app.py` từng bỏ qua hoàn toàn hai ô nhập ở sidebar. Sidebar cho nhập **OpenAI API key** và **model name**, có cả kiểm tra rỗng, nhưng dòng tạo model lại hardcode:

```python
llm = ChatOpenAI(model="gpt-5-mini", api_key=os.getenv("OPENAI_API_KEY"))   # bản cũ
```

Hệ quả: gõ model khác trong sidebar không có tác dụng, và nhập key vào sidebar mà `.env` không có `OPENAI_API_KEY` thì app vẫn lỗi — đúng cái tình huống mà ô nhập key sinh ra để giải quyết.

Đã sửa thành:

```python
llm = ChatOpenAI(model=model_name.strip(), api_key=api_key)
```

Kèm theo đó, `DEFAULT_MODEL` phải đổi từ `"gpt-5.6-sol"` (kế thừa từ file đề bài, không phải model id hợp lệ) sang `"gpt-5-mini"`. Trước đây giá trị này chỉ hiển thị cho đẹp nên sai cũng không sao; giờ nó thực sự được truyền cho `ChatOpenAI` thì phải đúng.

Bài học chung: nhận input từ người dùng, validate nó, rồi lại không dùng — đây là dạng bug UI không báo lỗi mà chỉ im lặng bỏ qua thao tác, thường khó phát hiện hơn crash.
