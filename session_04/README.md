# Buổi 4 — Structured Output: buộc LLM trả về dữ liệu có cấu trúc

Ngày học: 14/07/2026

## Mục tiêu

Ba buổi đầu, output của LLM luôn là **text tự do** — đọc thì được, nhưng muốn đưa vào chương trình (lưu DB, tính toán, render bảng) thì phải tự parse, mà parse text tự do rất mong manh.

Buổi 4 giải quyết đúng vấn đề đó: khai báo **schema** bằng Pydantic, và LLM trả về **object Python đã được validate**.

File minh hoạ: `docs/LLM_Structured_Output.ipynb` → bản đã làm là `LLM_Structured_Output.ipynb` ở thư mục gốc.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. Khai báo schema bằng Pydantic

```python
from pydantic import BaseModel, Field

class Movie(BaseModel):
    title: str    = Field(description="Tiêu đề/tên của bộ phim")
    year: int     = Field(description="Năm bộ phim được xuất bản")
    director: str = Field(description="Đạo diễn của bộ phim")
    rating: float = Field(description="Điểm đánh giá của bộ phim")
```

Ba thành phần của mỗi field:

| Thành phần | Vai trò |
| --- | --- |
| Tên field | Key trong kết quả |
| Type hint (`str`, `int`, `float`) | Ràng buộc kiểu — Pydantic validate sau khi model trả lời |
| `Field(description=...)` | **Chỉ dẫn cho LLM** hiểu phải điền gì vào |

`description` không phải comment cho người đọc — nó được gửi thẳng tới model như một phần của schema. Mô tả càng rõ, model điền càng đúng.

### 2. `with_structured_output()` — khác biệt trước và sau

```python
model = init_chat_model("groq:qwen/qwen3-32b")

# Trước
model.invoke("Hãy cung cấp cho tôi thông tin về bộ phim Obsession")
# → AIMessage(content='<think>...</think>\n\n**Bộ phim "Obsession" (2016)**\n- **Đạo diễn:** ...')
#   ~1300 token văn xuôi, muốn lấy đạo diễn phải tự regex

# Sau
model.with_structured_output(Movie).invoke("Hãy cung cấp cho tôi thông tin về bộ phim Obsession")
# → Movie(title='Obsession', year=2017, director='Daniele Lucchesi', rating=5.0)
#   object Python, truy cập .director ngay
```

Cùng một câu hỏi, cùng một model — chỉ khác một lời gọi hàm, output từ đoạn văn dài thành object dùng được ngay.

### 3. Bên trong, structured output = tool calling

In `model.with_structured_output(Movie)` ra sẽ thấy nó là một `RunnableBinding`:

```
kwargs={
  'tools': [{'type': 'function', 'function': {'name': 'Movie', 'parameters': {...JSON Schema...}}}],
  'tool_choice': {'type': 'function', 'function': {'name': 'Movie'}},
  'ls_structured_output_format': {'kwargs': {'method': 'function_calling'}}
}
| PydanticToolsParser(first_tool_only=True, tools=[Movie])
```

Cơ chế thật sự gồm 3 bước:

1. Class Pydantic được dịch sang **JSON Schema**.
2. Schema được đăng ký như một **function/tool** và `tool_choice` **ép** model phải gọi đúng tool đó.
3. `PydanticToolsParser` nhận arguments model sinh ra và dựng lại object `Movie`.

Hiểu điều này rất quan trọng: structured output và tool calling (buổi 5) là **cùng một cơ chế**, chỉ khác mục đích sử dụng.

### 4. `include_raw=True` — giữ lại cả phản hồi gốc

```python
model_with_structure = model.with_structured_output(Movie, include_raw=True)
response = model_with_structure.invoke("Provide details about the movie Inception")
```

Trả về dict 3 key:

| Key | Nội dung |
| --- | --- |
| `raw` | `AIMessage` gốc — có `tool_calls`, `reasoning_content`, token usage |
| `parsed` | `Movie(title='Inception', year=2010, director='Christopher Nolan', rating=8.8)` |
| `parsing_error` | `None` nếu parse thành công |

Không có `include_raw`, parse lỗi sẽ ném exception. Có `include_raw`, lỗi nằm ở `parsing_error` để tự xử lý — an toàn hơn cho code chạy thật.

### 5. Nested structure — schema lồng nhau

```python
class Actor(BaseModel):
    name: str
    role: str

class MovieDetails(BaseModel):
    title: str
    year: int
    cast: list[Actor]        # list các object
    genres: list[str]        # list string
    budget: float | None     # optional
```

LLM điền được cả cây object. Kết quả dùng như Python thuần:

```python
cast_lst = [actor.name for actor in response.cast]
# ['Michael Fassbender', 'Dakota Johnson', 'Shailene Woodley']
```

Ba kiểu field đáng nhớ: `list[Model]` (danh sách object), `list[str]` (danh sách giá trị), `X | None` (không bắt buộc — cho phép model bỏ trống thay vì bịa).

### 6. `create_agent(response_format=...)` — structured output ở tầng agent

```python
from langchain.agents import create_agent

agent = create_agent(model="gpt-5-mini", response_format=ContactInfo)
result = agent.invoke({"messages": [{"role": "user", "content": "Extract contact info from Tom Cruise"}]})
```

Kết quả có thêm key `structured_response` bên cạnh `messages`. Agent có thể chạy nhiều bước, nhưng câu trả lời cuối vẫn bị ép về đúng schema.

Kết quả thực tế đáng chú ý: `ContactInfo(name='Tom Cruise', email='', phone='')` — model **không bịa** email/phone mà để trống. Đây chính là hành vi mong muốn, và là lý do nên khai báo `| None` hoặc default cho các field có thể thiếu.

### 7. `init_chat_model()` — khởi tạo model bằng chuỗi

```python
model = init_chat_model("groq:qwen/qwen3-32b")
```

Cú pháp `"<provider>:<model>"` thay cho việc import đúng class (`ChatGroq`, `ChatOpenAI`). Tiện khi provider là tham số cấu hình.

## Bài tập đi kèm: CV Ranking

Project `cv_ranking/` (Next.js) + `cv_ranking_be/` (FastAPI) chấm và xếp hạng CV theo JD — áp dụng structured output ở quy mô thật.

Schema trong `cv_ranking_be/app/models.py` là ví dụ tốt về cách thiết kế schema nghiêm túc:

```python
class CriterionScore(BaseModel):
    name: str
    max_points: int
    awarded_points: float
    score_ratio: float = Field(ge=0, le=1)        # ràng buộc khoảng giá trị
    reason: str
    evidence: list[str] = Field(default_factory=list)

Recommendation = Literal["strong_match", "match", "potential", "weak_match", "not_match"]
```

Hai kỹ thuật mới so với notebook:

- **`Field(ge=..., le=...)`** — ràng buộc khoảng giá trị (`overall_score` trong [0, 100], `confidence_score` trong [0, 1]). Model trả sai khoảng thì Pydantic báo lỗi ngay.
- **`Literal[...]`** — enum, giới hạn model chỉ được chọn trong tập giá trị cho trước. Chắc chắn hơn nhiều so với viết "hãy trả về một trong các giá trị sau" trong prompt.

Và cách dùng trong `services/openai_scoring.py`:

```python
class LLMRankingPayload(BaseModel):     # schema bao ngoài, gói nhiều schema con
    job_profile: JobProfile
    rubric: list[RubricCriterion]
    candidates: list[CandidateScore]

llm = ChatOpenAI(model=model_name, temperature=0)
structured_llm = llm.with_structured_output(LLMRankingPayload)
payload = structured_llm.invoke(prompt)
```

Vài điểm đáng học từ prompt của nó:

- `temperature=0` cho tác vụ chấm điểm — cần kết quả nhất quán, không sáng tạo.
- Rubric được **serialize thành JSON rồi nhúng vào prompt** (`json.dumps(..., ensure_ascii=False, indent=2)`), thay vì mô tả bằng lời.
- Ràng buộc nghiệp vụ viết thẳng trong prompt: must-have là điều kiện loại, thiếu thì `qualified=false` và cap điểm ở 59; mọi tiêu chí phải kèm evidence trích từ CV; cấm dùng thuộc tính nhạy cảm (tuổi, giới tính, tôn giáo, ảnh…); cấm suy diễn thông tin không có trong CV.
- `truncate_text(text, max_chars=16000)` — cắt bớt input để không vượt context window, có đánh dấu `[TRUNCATED]`.
- Sắp xếp cuối cùng làm **bằng Python** (`candidates.sort(...)`), không giao cho LLM — việc gì code làm được chính xác thì đừng để model làm.

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `LLM_Structured_Output.ipynb` | Bản đã làm trong buổi học |
| `docs/LLM_Structured_Output.ipynb`, `docs/LLM Structured Output` | Tài nguyên gốc của giảng viên |
| `cv_ranking/` | Frontend Next.js — upload JD/CV, xem bảng xếp hạng |
| `cv_ranking_be/` | Backend FastAPI — parse PDF/DOCX, chấm bằng LLM (`openai_scoring.py`) hoặc heuristic (`scoring.py`) |
| `requirements.txt` | `streamlit`, `pandas`, `pydantic`, `langchain`, `langchain-openai`, `langchain-groq`, `pypdf`, `python-docx` |

## Cách chạy

```bash
pip install -r requirements.txt

# .env
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk_...

jupyter notebook LLM_Structured_Output.ipynb
```

CV Ranking: cài `cv_ranking_be/requirements.txt` rồi `uvicorn app.main:app --reload`, và `npm install && npm run dev` trong `cv_ranking/`.

## Tóm tắt: khi nào dùng gì

| Nhu cầu | Cách làm |
| --- | --- |
| Trả lời hội thoại cho người đọc | Text thường (buổi 1–3) |
| Trích xuất field vào DB / hiển thị bảng | `with_structured_output(Schema)` |
| Cần cả object lẫn metadata gốc, sợ parse lỗi | `with_structured_output(Schema, include_raw=True)` |
| Dữ liệu phân cấp (list object lồng nhau) | Nested Pydantic model |
| Giới hạn tập giá trị hợp lệ | `Literal[...]` |
| Ràng buộc khoảng số | `Field(ge=..., le=...)` |
| Field có thể thiếu | `X \| None` hoặc `default_factory` |
