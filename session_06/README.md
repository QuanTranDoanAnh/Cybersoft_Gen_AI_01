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
| `session_06_project/` | Project cuối buổi — BI copilot "InsightFlow" (Next.js + FastAPI + Postgres), mô tả ở dưới |

## Project cuối buổi — InsightFlow (`session_06_project/`)

Đề bài (từ `docs/docker-compose.yml`) là dựng một **BI copilot** hỏi đáp bằng ngôn ngữ tự nhiên trên bộ dữ liệu TV shows (TMDB), chạy trên Postgres và có UI thật. Bản đã làm nằm trong `session_06_project/`:

| Thành phần | Công nghệ |
| --- | --- |
| `frontend/` | Next.js 16 + React 19, Tailwind 4, zustand, ECharts, react-grid-layout |
| `backend/` | FastAPI, OpenAI SDK (Responses API), psycopg 3, sqlglot, pydantic-settings |
| `db` | Postgres 16, nạp sẵn 11 bảng từ `tvshows/*.csv` |
| `docker-compose.yml` | 3 service `db` → `backend` → `frontend`, nối bằng healthcheck |

### Luồng logic tổng thể

```
Người dùng gõ câu hỏi ở CopilotBar
  → POST /api/copilot/query {prompt}
  → run_copilot()
      1. _openai_plan()    GPT-5 + Responses API, text_format=CopilotPlan
                           → {dashboard_title, message, widgets[1..6]}
                             mỗi widget: {title, chart_type, sql, x_field, y_fields, ...}
      2. với từng widget:
           validate_and_limit_sql()   sqlglot: chặn DML, allow-list bảng, ép LIMIT
           execute_widget_plan()      psycopg chạy SQL thật trên Postgres
      3. _openai_insight()  gọi model lần 2, chỉ được dùng số liệu vừa truy vấn
  → CopilotResponse {title, message, mode, widgets[{..., data, sql, layout}]}
  → replaceDashboard() trong zustand store → arrangeWidgets() xếp lưới
  → react-grid-layout → ChartWidget → ECharts / bảng / thẻ KPI
```

Bốn endpoint: `/health`, `/api/meta` (tên model + chế độ copilot), `/api/dashboard/overview` (dashboard mặc định, SQL viết tay), `/api/copilot/query` (dashboard do LLM sinh).

### 12. Hai kiểu Text-to-SQL: agent vòng lặp vs. planner một lượt

Đây là điểm học lớn nhất của project — nó **không** dùng lại `SQLDatabaseToolkit`:

| | Notebook / `app.py` | `session_06_project/` |
| --- | --- | --- |
| Cơ chế | Agent + 4 tool, tự lặp nhiều vòng | **Một lần gọi** structured output |
| Biết schema nhờ | `sql_db_list_tables` + `sql_db_schema` lúc chạy | `SCHEMA_CONTEXT` viết cứng trong system prompt |
| Kiểm SQL | `sql_db_query_checker` (LLM soát LLM) | `sql_guard.py` (sqlglot, tất định) |
| Ai chạy SQL | Chính LLM, qua tool | Backend chạy, LLM không chạm DB |
| Output | Đoạn văn Markdown | JSON đúng schema `CopilotPlan` |

Lý do đổi cách: output ở đây không phải câu trả lời chữ mà là **đặc tả dashboard** để React render. Vòng lặp agent thì chậm, tốn token, và kết quả không đảm bảo đúng cấu trúc. Schema chỉ có 11 bảng nên nhét thẳng vào prompt rẻ hơn nhiều so với cho agent tự dò từng bước.

Bài học: *agent không phải lúc nào cũng là câu trả lời*. Khi schema nhỏ và biết trước, khi output cần đúng khuôn để máy khác đọc — một lần gọi có structured output vừa nhanh vừa dễ kiểm soát hơn.

### 13. Structured output là hợp đồng giữa LLM và UI

```python
class WidgetPlan(BaseModel):
    chart_type: Literal["bar", "line", "area", "pie", "scatter", "table", "kpi"]
    sql: str = Field(min_length=8, max_length=5_000)
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list, max_length=3)
    ...

client.responses.parse(model=..., input=[...], text_format=CopilotPlan)
```

`Literal` không chỉ để validate — nó đi vào JSON schema gửi cho OpenAI, nên model **không thể** sinh `chart_type="donut"`. Prompt còn ràng buộc: `x_field`, `y_fields`, `value_field` phải trùng đúng alias trong câu SQL, vì frontend tra dữ liệu bằng `row[widget.x_field]`.

Vì model vẫn có thể bỏ sót, code phòng hai lớp:

```python
# schemas.py — KPI thiếu value_field thì mặc định "value"
if self.chart_type == "kpi" and not self.value_field:
    self.value_field = "value"

# dashboard.py — nếu alias vẫn không khớp dữ liệu thật, lấy cột đầu tiên
if plan.chart_type == "kpi" and data and value_field not in data[0]:
    value_field = next(iter(data[0]))
```

Nguyên tắc: **validate ở schema, rồi đối chiếu lại với kết quả thật**. Schema chỉ đảm bảo hình dạng, không đảm bảo alias khớp dữ liệu.

### 14. `sql_guard.py` — chốt chặn tất định thay cho "prompt bảo đừng"

Ở buổi này, SQLite mở `mode=ro` là lớp bảo vệ; với Postgres, project dựng hẳn một validator chạy trước mọi câu SQL:

```python
def validate_and_limit_sql(sql: str) -> str:
    if ";" in candidate: ...                      # 1. chỉ một statement
    if FORBIDDEN_PATTERN.search(candidate): ...   # 2. chặn từ khoá DML/DDL
    expression = parse_one(candidate, read="postgres")   # 3. parse thành AST
    if not isinstance(expression, (exp.Select, exp.Union)): ...   # 4. phải là SELECT
    unknown_tables = referenced_tables - ALLOWED_TABLES  # 5. allow-list bảng
    ...
    expression = expression.limit(max_rows)       # 6. ép/kẹp LIMIT (500)
```

Năm điểm đáng học:

- **Parse thay vì regex.** Regex chỉ là lớp lọc thô; `sqlglot` dựng AST nên biết chắc câu lệnh là `SELECT`, biết chính xác bảng nào bị tham chiếu — không bị đánh lừa bởi chuỗi hay comment.
- **Allow-list, không phải deny-list.** Bảng lạ (`users`, `pg_*`) bị chặn mặc định; test `SELECT * FROM users` chính là để giữ tính chất này.
- **Trừ tên CTE trước khi so allow-list**, nếu không `WITH ranked AS (...) SELECT * FROM ranked` sẽ bị hiểu nhầm là bảng lạ.
- **Sửa thay vì chỉ từ chối.** Câu thiếu `LIMIT` được *thêm* `LIMIT 500`; câu xin 10.000 dòng bị *kẹp* xuống 500. Người dùng vẫn có kết quả, hệ thống vẫn an toàn.
- **Chặn cả thời gian chạy**: `SET LOCAL statement_timeout = 15000` trước mỗi truy vấn (`database.py`) — một câu JOIN tệ không treo cả API.

Ba tầng cộng lại: prompt (khuyên) → `sql_guard` (chặn) → quyền DB + timeout (giới hạn thiệt hại). Đúng tinh thần "phòng thủ nhiều lớp" của mục 7, nhưng ở mức production.

### 15. Gọi model hai lần: một để lập kế hoạch, một để bình luận

```python
plan = _openai_plan(prompt)          # lần 1: sinh SQL + đặc tả visual
results = [...]                      # chạy SQL thật
message = _openai_insight(prompt, plan, results)   # lần 2: viết nhận định
```

System prompt của lần 1 nói thẳng: *"Do not invent findings; a separate step will write insights after the queries have run."* Lần 2 chỉ nhận `question` + `dashboard_title` + **tối đa 25 dòng dữ liệu mỗi widget**, kèm ràng buộc *"Never add facts that are absent from the evidence."*

Đây là kỹ thuật chống bịa số liệu: model chỉ được bình luận **sau khi** có dữ liệu thật trong tay, và bằng chứng được cắt gọn để khỏi nổ token. Nếu lần 2 lỗi/timeout thì rơi về `plan.message` — dashboard vẫn dùng được vì phần bình luận chỉ là bonus.

### 16. Lỗi một phần không được giết cả dashboard

```python
for index, widget_plan in enumerate(plan.widgets):
    try:
        safe_sql = validate_and_limit_sql(widget_plan.sql)
        results.append(execute_widget_plan(widget_plan, safe_sql, index))
    except (UnsafeQueryError, Exception) as exc:   # xem ghi chú cuối file
        errors.append(f"{widget_plan.title}: {exc}")

if not results:
    raise ValueError("; ".join(errors) or "No valid widgets were generated")
if errors:
    message += f" Có {len(errors)} visual không thể tạo do truy vấn không hợp lệ."
```

LLM sinh 5 widget, 1 câu SQL sai cột → vẫn trả về 4 widget chạy được và nói rõ có 1 cái hỏng. Chỉ khi **không còn gì** mới báo lỗi 422. Với hệ thống mà một phần output do model sinh ra, "tất cả hoặc không gì cả" là lựa chọn tồi.

### 17. Chế độ demo — app vẫn chạy khi không có API key

```python
mode = "openai" if settings.openai_api_key else "demo"
plan = _openai_plan(prompt) if settings.openai_api_key else _demo_plan(prompt)
```

`_demo_plan()` bắt từ khoá (`genre`/`thể loại`, `country`/`quốc gia`, `year`/`năm`…) rồi trả về `CopilotPlan` viết sẵn — **cùng kiểu dữ liệu** với nhánh OpenAI, nên toàn bộ đường đi phía sau (guard → chạy SQL → render) không đổi một dòng. `/api/meta` phơi `copilot_mode` ra để UI hiện chấm vàng "Demo planner" thay vì tên model.

Bài học: cho nhánh fallback trả về **đúng type** của nhánh thật thì fallback gần như miễn phí; và trạng thái degrade phải hiển thị cho người dùng thấy.

### 18. Nạp dữ liệu: idempotent + `COPY FROM STDIN`

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(seed_database)   # không chặn event loop
    yield
```

```python
cursor.execute(SCHEMA_SQL)                 # CREATE TABLE IF NOT EXISTS
cursor.execute("SELECT COUNT(*) FROM shows")
if cursor.fetchone()[0] > 0:
    return                                 # đã nạp rồi thì thôi
... COPY {table} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, FORCE_NULL (...))
cursor.execute(INDEX_SQL)                  # tạo index SAU khi nạp
```

- `COPY ... FROM STDIN` nhanh hơn `INSERT` từng dòng nhiều lần; đọc theo chunk 1 MB nên không nuốt cả file vào RAM.
- `FORCE_NULL` biến ô rỗng trong CSV thành `NULL` thay vì chuỗi rỗng — nếu không, cột số sẽ lỗi kiểu.
- **Tạo index sau khi nạp**: nạp trước, index sau thì nhanh hơn hẳn so với vừa nạp vừa cập nhật index.
- `asyncio.to_thread` vì `psycopg` ở đây là sync — chạy thẳng trong `lifespan` sẽ chặn event loop.

Chi tiết đáng chú ý: cột trong dataset gốc viết sai chính tả là `eposide_run_time`, và code **giữ nguyên** — đồng thời ghi rõ trong prompt: *"The source column is intentionally named eposide_run_time."* Sửa tên cho đẹp thì phải sửa cả CSV; nói cho model biết sự thật thì rẻ hơn và không sai lệch dữ liệu.

### 19. Frontend: dashboard là state, không phải trang tĩnh

```ts
replaceDashboard: (title, widgets, message) =>
  set({ title, widgets: arrangeWidgets(widgets), copilotMessage: message, ... })
```

- **zustand** giữ cả `widgets` hiện tại lẫn `initialWidgets` — nhờ vậy nút *Reset dashboard* chỉ là `set({ widgets: state.initialWidgets })`.
- Copilot **thay thế** cả dashboard chứ không nối thêm widget (system prompt nói rõ: *"a complete replacement dashboard, not widgets to append"*).
- `arrangeWidgets()` xếp KPI lên hàng đầu, chart xuống dưới theo lưới 12 cột; `react-grid-layout` cho kéo–thả–resize, `onLayoutChange` ghi ngược vị trí vào store.
- `ChartWidget` chọn cách render theo `chart_type`: `kpi` → số lớn, `table` → bảng, còn lại → ECharts với option dựng từ `x_field`/`y_fields`.
- Nút **`{ }` Generated SQL** trên mỗi widget hiện lại câu SQL đã chạy — cùng tinh thần "hiện SQL đã dùng" ở mục 10 và `ToolTrace` buổi 5: người dùng phải kiểm chứng được con số đến từ đâu.

### 20. Docker Compose: thứ tự khởi động và biến môi trường build-time

```yaml
backend:
  depends_on:
    db: { condition: service_healthy }
frontend:
  build:
    args:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
  depends_on:
    backend: { condition: service_healthy }
```

- `condition: service_healthy` chứ không chỉ `depends_on` trần: backend seed dữ liệu lúc startup nên phải đợi Postgres thật sự sẵn sàng; healthcheck của backend có `start_period: 45s` để chừa thời gian nạp CSV.
- `NEXT_PUBLIC_*` của Next.js được **nhúng vào bundle lúc build**, nên phải truyền qua `build.args` — đặt ở `environment` thôi là không đủ.
- `frontend` build theo multi-stage với `output: "standalone"`, chạy bằng user không phải root (`USER nextjs`).

## Cách chạy

```bash
pip install -r requirements.txt

# .env
# OPENAI_API_KEY=sk-...

python chinhook_db.py                # tải Chinook.db về (chỉ cần cho notebook)
jupyter notebook Agent_SQL.ipynb

streamlit run app.py                 # chatbot trên student.db
```

Project cuối buổi:

```bash
cd session_06_project

# .env.docker  (đã được .gitignore bỏ qua — không commit)
# POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
# OPENAI_API_KEY=sk-...        để trống nếu muốn chạy chế độ demo
# OPENAI_MODEL=gpt-5-mini

docker compose --env-file .env.docker up --build
# frontend  http://localhost:3000
# backend   http://localhost:8000/health

# test cho phần guard/schema
cd backend && pytest
```

Lần chạy đầu backend sẽ nạp ~8 MB CSV trong `tvshows/` vào Postgres (mất vài chục giây); các lần sau `seed_database()` thấy bảng `shows` đã có dữ liệu nên bỏ qua.

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

### Vài điểm còn lệch trong project (đọc code phát hiện được)

**`gpt-5.6-sol` xuất hiện lại.** `backend/app/config.py` để `openai_model: str = "gpt-5.6-sol"`, và `docker-compose.yml` cũng mặc định `OPENAI_MODEL: ${OPENAI_MODEL:-gpt-5.6-sol}`. Đúng cái model id không hợp lệ đã phải sửa trong `app.py`. Hiện app vẫn chạy vì `.env.docker` đặt `OPENAI_MODEL=gpt-5-mini` đè lên; nhưng ai clone repo rồi chạy mà quên set biến này sẽ gặp lỗi từ OpenAI ở lần hỏi đầu tiên — mà thông báo lỗi chỉ hiện lên UI dưới dạng 422. Nên đổi default ở cả hai chỗ thành `gpt-5-mini`.

**`.env.docker.example` không khớp `docker-compose.yml`.** File example liệt kê `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DATABASE`, `JWT_SECRET`, `SESSION_COOKIE_SECURE`, `APP_PORT` — compose **không đọc** biến nào trong số đó. Ngược lại, ba biến compose thật sự cần (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) lại không có trong example. Copy example thành `.env.docker` rồi đặt mật khẩu mạnh vào `DB_PASS` thì Postgres vẫn khởi động bằng `copilot/copilot` mặc định — lại đúng dạng bug "nhập vào rồi bị bỏ qua trong im lặng" như trên, chỉ khác là lần này hậu quả là bảo mật.

**`_layout()` ở backend gần như là code chết.** `dashboard.py` tính sẵn `{x, y, w, h}` cho từng widget, nhưng frontend `arrangeWidgets()` xếp lại toàn bộ trong cả `setOverview` lẫn `replaceDashboard`, nên giá trị từ backend luôn bị ghi đè. Hai chỗ cùng chịu trách nhiệm bố cục thì sớm muộn cũng lệch nhau — nên bỏ hẳn một bên.

**`except (UnsafeQueryError, Exception)` trong `copilot.py` là thừa.** `UnsafeQueryError` kế thừa `ValueError` nên đã nằm trong `Exception`; viết vậy dễ khiến người đọc tưởng hai nhánh được xử lý khác nhau. Nếu muốn nói rõ ý "SQL không an toàn cũng chỉ là một lỗi widget", tách hai `except` với thông điệp khác nhau sẽ đúng hơn.
