# Cybersoft_Gen_AI_01

Ghi chép và bài tập khoá **Generative AI & AI Agent** của Cybersoft.

Mỗi buổi học nằm trong một thư mục `session_XX/` kèm README riêng tóm tắt lý thuyết rút ra từ đoạn mã minh hoạ. File này là mục lục và bản đồ kiến thức của cả khoá.

## Mục lục các buổi

| # | Buổi | Ngày học | Nội dung chính | Trạng thái code |
| --- | --- | --- | --- | --- |
| 1 | [Gọi OpenAI API & chatbot có ngữ cảnh](session_01/README.md) | 04/07/2026 | OpenAI SDK, `messages`, Streamlit, lưu lịch sử JSON | ✅ Đầy đủ |
| 2 | [LangChain, Groq và memory theo `session_id`](session_02/README.md) | 07/07/2026 | LCEL, `ChatPromptTemplate`, `RunnableWithMessageHistory` | ✅ Đầy đủ |
| 3 | [Document Loader và tóm tắt văn bản dài](session_03/README.md) | 11/07/2026 | `YoutubeLoader`, chunking, map-reduce, `StrOutputParser` | ✅ Đầy đủ |
| 4 | [Structured Output](session_04/README.md) | 14/07/2026 | Pydantic schema, `with_structured_output()`, nested model | ✅ Đầy đủ |
| 5 | [Tool Calling](session_05/README.md) | 17/07/2026 | `@tool`, `bind_tools()`, vòng lặp agent, human-in-the-loop | ✅ Đầy đủ |
| 6 | [SQL Agent](session_06/README.md) | 20/07/2026 | `SQLDatabaseToolkit`, `create_agent()`, `agent.stream()` | ✅ Đầy đủ |
| 7 | [HuggingFace `transformers` & Reasoning Prompting](session_07/README.md) | 24/07/2026 | BART, tokenizer/logits, CoT / ToT / Self-Consistency | 📄 Mới có tài liệu |
| 8 | [HF Inference qua LangChain & đóng gói production](session_08/README.md) | 27/07/2026 | `ChatHuggingFace`, Docker Compose làm cứng bảo mật | 📄 Mới có tài liệu |

## Mạch kiến thức

Khoá học đi theo một đường thẳng: từ **gọi được LLM** → **kiểm soát được output** → **cho LLM hành động** → **đưa lên production**.

```
b1  Gọi API thô                    LLM trả lời được
b2  LangChain + memory             ...nhớ được hội thoại
b3  Document Loader                ...đọc được dữ liệu ngoài
b4  Structured Output              ...trả về dữ liệu máy dùng được
b5  Tool Calling                   ...gọi được hàm, làm được việc
b6  SQL Agent                      ...tự truy vấn database
b7  Open-source model + Reasoning  ...chạy model mở, suy luận nhiều bước
b8  HF Inference + Docker          ...đóng gói và triển khai
```

Ba chủ đề xuyên suốt, mỗi buổi bồi thêm một lớp:

**1. Quản lý ngữ cảnh** — API là stateless, ngữ cảnh luôn là việc của phía client.

| Buổi | Cách làm |
| --- | --- |
| 1 | Tự append vào list `messages`, lưu file JSON |
| 2 | `RunnableWithMessageHistory` + `store` theo `session_id`, `trim_history()` |
| 3 | Tự implement `BaseChatMessageHistory` để lịch sử nằm trong database |
| 5–6 | Agent state — `messages` tích luỹ cả `AIMessage` lẫn `ToolMessage` |

**2. Kiểm soát output** — càng về sau càng chặt.

| Buổi | Cách làm |
| --- | --- |
| 1–3 | Text tự do, ép định dạng bằng lời trong prompt |
| 4 | Pydantic schema + `Field(ge/le)` + `Literal[...]` — validate được |
| 5 | Tool call — model trả về tên hàm + tham số có schema |
| 6 | SQL có `query_checker` soát lại trước khi chạy |
| 7 | Ép format `Answer: <x>` để chấm điểm tự động, có fallback regex |

**3. Minh bạch và an toàn** — hệ thống AI phải cho người dùng kiểm chứng được.

| Buổi | Cách làm |
| --- | --- |
| 3 | "Giữ đúng ý, không bịa" viết thẳng vào prompt |
| 4 | Cấm suy diễn thông tin không có trong CV, cấm dùng thuộc tính nhạy cảm |
| 5 | `ToolTrace` ghi lại mọi lời gọi; tool ghi dữ liệu phải qua người phê duyệt |
| 6 | Hiện lại câu SQL đã dùng; connection mở **read-only** ở tầng driver |
| 8 | Hiện cả tóm tắt từng chunk lẫn transcript gốc; container `read_only` |

## Nội dung từng buổi

### [Buổi 1 — Gọi OpenAI API & chatbot có ngữ cảnh](session_01/README.md)

Bài học cốt lõi: **API của LLM là stateless**. Server không nhớ lượt chat trước, muốn bot nhớ thì client phải gửi lại toàn bộ lịch sử mỗi request. Ba file thể hiện ba mức: terminal → Streamlit không nhớ → Streamlit có nhớ + lưu JSON. Kèm `st.session_state` và vì sao Streamlit cần nó.

### [Buổi 2 — LangChain, Groq và memory theo `session_id`](session_02/README.md)

LangChain chuẩn hoá interface giữa các provider — `ChatOpenAI` và `ChatGroq` dùng chung `.invoke()`. Giới thiệu LCEL (`prompt | model`), `ChatPromptTemplate` có biến, và `RunnableWithMessageHistory` đóng gói toàn bộ việc quản lý lịch sử. Thí nghiệm hai `session_id` chứng minh các cuộc hội thoại được cô lập.

### [Buổi 3 — Document Loader và tóm tắt văn bản dài](session_03/README.md)

Đưa dữ liệu ngoài vào LLM. `YoutubeLoader` trả về `list[Document]` — kiểu dữ liệu chuẩn của toàn hệ sinh thái. Transcript video dài vượt context window nên phải chunking + **map-reduce**: `.batch()` tóm tắt từng chunk song song, rồi gộp lại. Thêm `StrOutputParser` và `@st.cache_data`.

### [Buổi 4 — Structured Output](session_04/README.md)

Khai báo schema bằng Pydantic, LLM trả về **object Python đã validate** thay vì đoạn văn phải tự regex. Điểm quan trọng: bên trong, `with_structured_output()` chính là **tool calling** với `tool_choice` ép buộc — cầu nối sang buổi 5. Kèm nested schema, `include_raw=True`, và `Literal[...]` / `Field(ge=, le=)` từ project CV Ranking.

### [Buổi 5 — Tool Calling](session_05/README.md)

`@tool` biến hàm Python thành tool, **docstring là phần prompt** quyết định model chọn đúng hay sai. Điểm dễ hiểu nhầm nhất: model **không tự chạy hàm**, nó chỉ đề nghị — thực thi là việc của code mình, và đó là ranh giới an toàn. Vòng lặp agent đầy đủ với `ToolMessage` + `tool_call_id`, human-in-the-loop cho tool ghi dữ liệu.

### [Buổi 6 — SQL Agent](session_06/README.md)

Dùng toolkit dựng sẵn thay vì tự viết tool. `SQLDatabaseToolkit` cho 4 tool theo đúng quy trình một data analyst: liệt kê bảng → xem schema → **nhờ LLM soát câu SQL** → chạy. `agent.stream()` cho thấy agent tự quyết định cả chuỗi 4 bước. Nhấn mạnh phòng thủ nhiều lớp: prompt cấm DML là lớp một, connection read-only mới là lớp không vượt qua được.

### [Buổi 7 — HuggingFace `transformers` & Reasoning Prompting](session_07/README.md)

Xuống một tầng trừu tượng: tự tokenize, đọc `logits`, tự decode — để thấy bên trong `.invoke()` có gì. BART minh hoạ "một base model, nhiều head". Phần hai là 4 cấp prompt cho bài toán suy luận: Normal → Chain-of-Thought → Tree-of-Thought → Self-Consistency, đo trên bộ MATH-500 với seed cố định.

### [Buổi 8 — HF Inference qua LangChain & đóng gói production](session_08/README.md)

Làm lại đúng bài buổi 3 nhưng bằng model open-source qua `ChatHuggingFace` — kiểm chứng lời hứa của buổi 2: đổi provider mà chain không đổi. Phần Docker Compose là bản hoàn chỉnh nhất khoá: YAML anchor, `read_only` + `tmpfs`, `no-new-privileges`, log rotation, healthcheck chạy `SELECT 1`.

## Các project thực hành

| Buổi | Project | Stack | Trạng thái |
| --- | --- | --- | --- |
| 1 | `genai-shopai` + `genai-shopai-be` | Next.js + Python | Có code |
| 3 | `genai-shopai-ver2` + `-be` | Next.js + FastAPI + Supabase | Có code |
| 4 | `cv_ranking` + `cv_ranking_be` | Next.js + FastAPI, chấm CV theo JD | Có code |
| 5 | `ai_business_copilot` + `...busi_be` | Next.js + FastAPI + Postgres + Docker | Có code, có test |
| 6 | BI copilot trên dữ liệu TV shows | Postgres + backend + frontend | Mới có `docker-compose.yml` |
| 7 | STEM Reasoning Lab | Postgres + FastAPI + Next.js, HF Inference | Mới có compose + test cases |
| 8 | ScholarTube Edu | Postgres + backend + frontend, HF Inference | Mới có compose |

## Công nghệ dùng trong khoá

| Nhóm | Thành phần |
| --- | --- |
| LLM provider | OpenAI, Groq, Hugging Face Inference |
| Framework | LangChain (`langchain-core`, `-openai`, `-groq`, `-community`, `-huggingface`), `transformers` |
| Giao diện | Streamlit (buổi 1–3, 6, 8), Next.js + Tailwind (các project fullstack) |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Dữ liệu | SQLite, Postgres, Supabase, MySQL |
| Hạ tầng | Docker Compose, `python-dotenv` |

## Quy ước chung

- Mỗi `session_XX/` có `requirements.txt` riêng — nên tạo virtualenv riêng cho từng buổi.
- API key luôn đặt trong `.env` của thư mục buổi đó, **không commit**:

  ```
  OPENAI_API_KEY=sk-...
  GROQ_API_KEY=gsk_...
  HF_TOKEN=hf_...
  ```

- `docs/` trong mỗi buổi chứa tài nguyên gốc của giảng viên (thường là notebook có các hàm để trống); file cùng tên ở thư mục cha là bản đã làm.

```bash
cd session_XX
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
```
