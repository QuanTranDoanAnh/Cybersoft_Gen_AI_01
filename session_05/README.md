# Buổi 5 — Tool Calling: cho LLM gọi được hàm của mình

Ngày học: 17/07/2026

## Mục tiêu

Đến buổi 4, LLM vẫn chỉ biết những gì có trong dữ liệu huấn luyện và trong prompt. Nó không tra được database, không đọc được web, không tính toán chính xác.

Buổi 5 mở khoá điều đó: **tool calling** — mình khai báo một số hàm Python, model tự quyết định gọi hàm nào với tham số gì.

File minh hoạ: `docs/[Resource] LangChain_Tool_Calling_OpenAI.ipynb` → bản đã làm là `[Resource] LangChain_Tool_Calling_OpenAI.ipynb` ở thư mục gốc.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. Decorator `@tool` — biến hàm Python thành tool

```python
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply a and b."""
    return a * b

multiply.invoke({"a": 2, "b": 8})   # 16
```

`@tool` đọc chữ ký hàm và tạo ra một `Tool` object. Ba thứ được gửi cho model:

| Trong code            | Model nhìn thấy                                          |
| --------------------- | -------------------------------------------------------- |
| Tên hàm               | Tên tool                                                 |
| **Docstring**         | Mô tả — model dựa vào đây để quyết định có gọi hay không |
| Type hint của tham số | JSON Schema của arguments                                |

**Docstring không phải comment.** Nó là phần prompt quyết định model chọn đúng tool hay không. Hàm không có docstring sẽ lỗi.

Tool gọi tay bằng `.invoke({...})` với dict — không phải `multiply(2, 8)`.

### 2. `bind_tools()` — đăng ký tool với model

```python
llm = ChatOpenAI(model="gpt-5-mini", api_key=os.getenv("OPENAI_API_KEY"))

tools = [reverse_string, multiply, search_wikipedia, search_arxiv, load_web_page]
model_with_tools = llm.bind_tools(tools)
```

Đây chính là kỹ thuật đã gặp ở buổi 4 — `with_structured_output()` bên trong cũng gọi `bind_tools` với `tool_choice` ép buộc. Khác biệt: ở đây model được **tự do chọn** gọi tool nào, hoặc không gọi tool nào cả.

### 3. Model **không** tự chạy hàm — nó chỉ đề nghị

Đây là điểm dễ hiểu nhầm nhất của buổi:

```python
response = model_with_tools.invoke("Tìm kiếm thông tin về bài báo khoa học 'Attention is all you need'")

for tool_call in response.tool_calls:
    print(tool_call)
# {'name': 'search_arxiv',
#  'args': {'query': 'Attention is all you need', 'top_k': 2},
#  'id': 'call_10GuH7IGXguaDMYYoSg7KSvv',
#  'type': 'tool_call'}
```

`AIMessage` trả về có `content=''` và `finish_reason='tool_calls'`. Model chỉ nói **"hãy gọi hàm này với tham số này"** — việc thực thi là của code mình. Đây là ranh giới an toàn quan trọng: mình toàn quyền kiểm tra/từ chối trước khi chạy.

Mỗi tool call có `id` — cần dùng để nối kết quả trả về đúng chỗ (mục 6).

### 4. Automatic routing — model tự chọn tool theo ngữ cảnh

Notebook có sẵn test chứng minh:

```python
routing_cases = [
    ("Chỉ dùng Wikipedia để tìm thông tin về Hà Nội.", "search_wikipedia"),
    ("Chỉ dùng arXiv để tìm nghiên cứu về large language model agents.", "search_arxiv"),
    ("Hãy đọc URL https://example.com bằng công cụ tải trang web.", "load_web_page"),
]
for prompt, expected_name in routing_cases:
    routed = model_with_tools.invoke(prompt)
    assert routed.tool_calls[0]["name"] == expected_name
```

Cả ba đều PASS. Model phân biệt được dựa hoàn toàn vào **docstring tiếng Việt** của từng tool. Cách viết test bằng `assert` như trên cũng là cách kiểm chứng routing đáng học.

### 5. Document Loader thành tool

Buổi 3 dùng `YoutubeLoader` thủ công. Buổi 5 bọc loader vào trong tool để model tự gọi:

```python
@tool
def search_wikipedia(query: str, top_k: int = 2) -> str:
    """Tìm thông tin bách khoa trên Wikipedia."""
    try:
        documents = load_with_retry(lambda: WikipediaLoader(query=query, load_max_docs=top_k, lang="vi"))
        return format_documents(documents)
    except Exception as loader_exc:
        try:    # fallback: đọc thẳng URL bài viết
            article_url = f"https://vi.wikipedia.org/wiki/{quote(query.strip().replace(' ', '_'))}"
            return format_documents(WebBaseLoader(web_paths=(article_url,), ...).load())
        except Exception as fallback_exc:
            return f"Wikipedia hiện không truy cập được: ..."
```

Ba pattern đáng học về **độ bền của tool**:

- **`format_documents()`** — tool phải trả về `str`, nên `list[Document]` (chuẩn dữ liệu của buổi 3) được ép về text gọn, cắt ở `max_chars=4000` để không nổ context window.
- **`load_with_retry()`** — retry với delay tăng dần cho lỗi mạng tạm thời.
- **Trả lỗi dưới dạng chuỗi, không raise** — model đọc được "nguồn này không truy cập được" và tự xoay sang cách khác. Ném exception thì cả vòng lặp agent chết.

Notebook còn phải vá `wikipedia` và `arxiv` để ép dùng HTTPS — bài học thực tế về việc thư viện cũ hay hỏng lặt vặt.

### 6. Vòng lặp agent — nối kết quả tool trở lại model

Notebook dừng ở chỗ model đề nghị gọi tool. Vòng lặp đầy đủ nằm trong `ai_business_copilotbusi_be/app/copilot.py`:

```python
messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]

for _ in range(4):                                   # giới hạn số bước
    ai_message = model_with_tools.invoke(messages)
    messages.append(ai_message)

    if not ai_message.tool_calls:                    # model đã có câu trả lời → dừng
        return CopilotResponse(answer=str(ai_message.content), ...)

    for call in ai_message.tool_calls:
        result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
        messages.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False, default=str),
            tool_call_id=call["id"],                 # nối đúng với tool call đã đề nghị
        ))
```

Bốn điểm cốt lõi:

1. **`ToolMessage`** — loại message thứ tư, bên cạnh system/human/AI. Đây là cách đưa kết quả hàm trở lại cho model.
2. **`tool_call_id`** phải khớp với `id` model đã sinh ra, nếu không model không biết kết quả này thuộc lời gọi nào.
3. **Lặp**, vì sau khi có kết quả model có thể muốn gọi tiếp tool khác.
4. **`for _ in range(4)`** — luôn giới hạn số vòng, tránh loop vô hạn (và cháy tiền API).

`TOOLS_BY_NAME = {item.name: item for item in TOOLS}` là cách tra tool từ tên model trả về.

### 7. Human-in-the-loop — tool chỉ _đề xuất_, người duyệt

Tool đọc dữ liệu thì chạy thẳng. Tool **ghi** dữ liệu thì không:

```python
@tool
def propose_follow_up_task(customer_id, assignee, due_date, description) -> dict:
    """Tạo đề xuất công việc follow-up; cần người dùng phê duyệt trước khi ghi dữ liệu."""
    return {
        "requires_approval": True,
        "action": "create_follow_up_task",
        "payload": {...},
        "reason": "Thao tác này sẽ tạo công việc mới trong hệ thống.",
    }
```

Vòng lặp phát hiện cờ này và tách ra thành một `ApprovalProposal` gửi lên UI, thay vì ghi DB ngay. System prompt cũng nhắc lại: _"Các thao tác ghi dữ liệu chỉ được tạo đề xuất chờ người dùng phê duyệt."_

Nguyên tắc chung: **tool đọc thì tự do, tool ghi thì phải qua người duyệt.**

### 8. Trace — ghi lại model đã gọi gì

```python
traces.append(ToolTrace(
    tool=call["name"],
    arguments=call["args"],
    result=json.dumps(result, ensure_ascii=False, default=str),
))
```

Mỗi lời gọi tool được lưu lại và trả về cho frontend. Hai lợi ích: debug được khi agent trả lời sai, và người dùng thấy được câu trả lời dựa trên dữ liệu nào (`build_visualizations()` còn dựng luôn biểu đồ KPI/donut/bar từ chính các trace này).

### 9. Chống bịa số liệu bằng system prompt

```
Bạn là AI Copilot cho hệ thống quản trị doanh nghiệp.
Trả lời ngắn gọn bằng tiếng Việt, dựa trên dữ liệu tool. Không tự bịa số liệu.
```

Có tool rồi vẫn phải nói rõ: chỉ dùng số từ tool, không tự chế. Kết hợp với trace ở trên để kiểm chứng được.

### 10. Chế độ demo không cần API key

`local_demo_response()` bắt keyword ("quá hạn", "báo cáo", "thị trường"…) rồi gọi thẳng tool tương ứng, bỏ qua LLM. App vẫn dùng được để xem UI/biểu đồ khi chưa có key — cùng tinh thần với chế độ Demo của buổi 2.

## Bài tập đi kèm: AI Business Copilot

| Thư mục                       | Nội dung                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| `ai_business_copilot/`        | Frontend Next.js — chat + dashboard + biểu đồ, proxy API qua `app/api/[...path]/route.ts`     |
| `ai_business_copilotbusi_be/` | Backend FastAPI — `copilot.py` (agent + 6 tool), `store.py`, `auth.py`, Postgres, có `tests/` |
| `docker-compose.yaml`         | Postgres + backend + frontend, có healthcheck và thứ tự khởi động                             |

Bộ tool của Copilot: `get_dashboard_metrics`, `get_operations_report`, `find_inactive_customers`, `get_overdue_tasks`, `propose_follow_up_task`, `research_web`.

Riêng `research_web` dùng **OpenAI Web Search** (`tools=[{"type": "web_search"}]` qua Responses API) — tức là một tool phía server của OpenAI được bọc lại thành tool của mình.

### Điểm mới về mặt hạ tầng: `docker-compose.yaml`

Buổi đầu tiên trong khoá đóng gói cả hệ thống bằng Docker:

- **`${DB_USER:?DB_USER is required}`** — bắt buộc phải có biến, thiếu là compose fail ngay thay vì chạy sai.
- **`${OPENAI_MODEL:-gpt-4o-mini}`** — giá trị mặc định khi biến trống.
- **`healthcheck` + `depends_on: condition: service_healthy`** — backend chỉ khởi động khi Postgres thật sự sẵn sàng, frontend chỉ khởi động sau backend.
- **`expose` vs `ports`** — backend chỉ mở trong mạng nội bộ `orbit_internal`, chỉ frontend publish ra ngoài. Database không lộ ra host.
- **`volumes: postgres_data`** — dữ liệu sống sót qua `docker compose down`.

## Cách chạy

```bash
pip install -r requirements.txt
jupyter notebook "[Resource] LangChain_Tool_Calling_OpenAI.ipynb"
```

AI Business Copilot (toàn bộ stack):

```bash
cp .env.docker.example .env.docker
# điền DB_USER / DB_PASS / DATABASE / JWT_SECRET / OPENAI_API_KEY
docker compose --env-file .env.docker up --build
# → http://localhost:3000
```

## Ghi chú

`get_dashboard_metrics()` trong `ai_business_copilotbusi_be/app/copilot.py` từng viết `task.status is not "done"`. `is not` so sánh **định danh object** chứ không so sánh giá trị — với chuỗi lấy từ DB, biểu thức này gần như luôn trả `True`, nên `open_tasks` đếm lẫn cả task đã hoàn thành, kéo theo cả `overdue_tasks` sai. Đã sửa thành `!=` (giống `get_overdue_tasks()` vốn viết đúng ngay từ đầu).

Bài học chung: với `str`, `int` hay bất kỳ giá trị nào, luôn dùng `==` / `!=`. Chỉ dùng `is` / `is not` cho `None`, `True`, `False`.

## Mạch kiến thức cả khoá

| Buổi | Thêm được điều gì                                                       |
| ---- | ----------------------------------------------------------------------- |
| 1    | Gọi LLM, tự quản lý ngữ cảnh — API là stateless                         |
| 2    | LangChain trừu tượng hoá provider, memory theo `session_id`             |
| 3    | Đưa dữ liệu ngoài vào (Document Loader), xử lý văn bản dài (map-reduce) |
| 4    | Output có cấu trúc, validate được (Pydantic + `with_structured_output`) |
| 5    | LLM **hành động** được: gọi tool, vòng lặp agent, human-in-the-loop     |
