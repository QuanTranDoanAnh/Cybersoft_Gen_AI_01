# Buổi 8 — Hugging Face Inference qua LangChain, và đóng gói production

Ngày học: 27/07/2026

> **Trạng thái:** thư mục hiện chỉ có `docs/` — chưa có notebook/app bài làm. README này tóm tắt nội dung suy ra từ hai file trong `docs/`.

## Mục tiêu

Buổi 8 khép lại vòng tròn của cả khoá: **làm lại đúng bài toán của buổi 3** (tóm tắt video YouTube), nhưng thay OpenAI/Groq bằng **model open-source trên Hugging Face** — và lần này đóng gói ở mức production.

Đây là bài kiểm chứng cho lời hứa từ buổi 2: nếu LangChain thực sự trừu tượng hoá được provider, thì đổi backend model chỉ cần sửa vài dòng, phần chain giữ nguyên.

File minh hoạ: `docs/HuggingFace Youtube Summarizer` và `docs/docker-compose.yaml`.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. `HuggingFaceEndpoint` + `ChatHuggingFace` — HF nói ngôn ngữ của LangChain

```python
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

def build_chat_model(hf_token: str, repo_id: str, max_new_tokens: int = 800):
    """Dùng Hugging Face Inference (provider auto) qua LangChain HuggingFaceEndpoint"""
```

Hai class, hai vai trò tách bạch:

| Class | Vai trò |
| --- | --- |
| `HuggingFaceEndpoint` | Lớp giao tiếp thô với HF Inference API — `repo_id`, `huggingfacehub_api_token`, `max_new_tokens`, `temperature` |
| `ChatHuggingFace` | Bọc endpoint đó thành **chat model** chuẩn LangChain — có `.invoke()`, trả `AIMessage` |

Phải qua hai lớp vì HF Inference API vốn là API **text generation** thuần, không có khái niệm role `system`/`user`/`assistant`. `ChatHuggingFace` chịu trách nhiệm áp **chat template** của từng model để chuyển list message thành một chuỗi prompt đúng định dạng model đó mong đợi.

So sánh với các buổi trước — đây là điểm quan trọng nhất của buổi:

```python
llm = ChatOpenAI(model="gpt-5-mini")                            # buổi 1, 2, 4, 5, 6
llm = ChatGroq(model="qwen/qwen3-32b")                          # buổi 2, 3
llm = ChatHuggingFace(llm=HuggingFaceEndpoint(repo_id="..."))   # buổi 8
```

Ba provider hoàn toàn khác nhau, cùng một interface. Toàn bộ code phía sau (`.invoke()`, `.content`, chain, map-reduce) không đổi.

### 2. `repo_id` — model là một tham số, không phải hằng số

```python
repo_id = st.text_input("Model repo_id", value="Qwen/Qwen2.5-7B-Instruct")
```

Trên Hugging Face, model được định danh bằng `<tổ chức>/<tên model>`. Đây là kho model mở lớn nhất hiện nay — người dùng gõ tên khác là đổi được model ngay, không cần sửa code.

Đánh đổi so với API thương mại: model 7B chạy nhanh, rẻ (hoặc miễn phí ở mức thấp), tự chủ được — nhưng chất lượng suy luận thấp hơn các model lớn, và không phải `repo_id` nào cũng có sẵn Inference endpoint (đó là lý do đoạn xử lý lỗi trong app nhắc tới trường hợp "model không được cấp quyền").

### 3. Tái sử dụng nguyên xi kỹ thuật của buổi 3

```python
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders.youtube import TranscriptFormat
```

`YoutubeLoader` + `TranscriptFormat.CHUNKS` + `chunk_seconds` — y hệt buổi 3. Điểm mới trong docstring của hàm loader:

```python
"""
QUAN TRỌNG:
- add_video_info=False để tránh pytube (hay lỗi HTTPError)
- Transcript lấy qua youtube-transcript-api
"""
```

`pytube` (thư viện lấy metadata video) thường xuyên hỏng khi YouTube đổi giao diện. Tắt `add_video_info` thì chỉ còn phụ thuộc `youtube-transcript-api` — bớt một điểm gãy. Bài học chung: **cắt bỏ dependency không thực sự cần**, nhất là loại hay hỏng.

App còn thêm hai tuỳ chọn transcript mà buổi 3 không có:

- `preferred_langs` (mặc định `"vi,en"`) — thứ tự ưu tiên ngôn ngữ phụ đề.
- `translate_to` — nhờ YouTube dịch phụ đề sẵn, thay vì bắt LLM vừa dịch vừa tóm tắt.

### 4. Map-reduce viết tay bằng vòng lặp

```python
def summarize_docs_map_reduce(chat_model, docs, output_language: str = "vi"):
    chunk_summaries = []
    for i, d in enumerate(docs, start=1):
        chunk_text = (d.page_content or "").strip()
        if not chunk_text:
            continue
        prompt = f"""...Hãy tóm tắt chunk #{i} ... bằng tiếng {output_language}
- 5–8 gạch đầu dòng
- Giữ đúng nội dung transcript, không bịa
TRANSCRIPT CHUNK:
{chunk_text}"""
        resp = chat_model.invoke(prompt)
        chunk_summaries.append((resp.content or "").strip())
```

Khác buổi 3 ở chỗ: buổi 3 dùng `chunk_chain.batch(inputs)` chạy song song, ở đây là vòng `for` tuần tự.

Đây là đánh đổi có lý do: HF Inference API ở tier miễn phí dễ bị **rate limit**, bắn 20 request song song sẽ ăn 429. Chạy tuần tự chậm hơn nhưng an toàn hơn. (Cấu hình Docker ở dưới xử lý vấn đề này theo cách khác — batch có kiểm soát.)

Hai chi tiết phòng thủ nhỏ nhưng đáng học:

- `(d.page_content or "").strip()` và `if not chunk_text: continue` — bỏ qua chunk rỗng, tránh gọi API vô ích.
- `(resp.content or "").strip()` — `.content` có thể là `None`, không giả định nó luôn là string.

Tầng reduce ép cấu trúc rõ ràng, kèm câu chốt **"Chỉ dùng thông tin từ chunk summary, không được bịa thêm"**:

```
1) TL;DR (2–4 câu)
2) Ý chính (6–12 bullet)
3) Dàn ý theo mục (nếu phù hợp)
4) Điểm đáng chú ý (3–6 bullet)
5) (Tuỳ chọn) Việc cần làm / Bài học rút ra
```

### 5. Hiện cả kết quả trung gian cho người dùng

```python
left, right = st.columns([1.2, 1], gap="large")
with left:
    st.subheader("✅ Tóm tắt cuối cùng")
with right:
    st.subheader("🧩 Tóm tắt từng chunk")
    for i, s in enumerate(chunk_summaries, start=1):
        with st.expander(f"Chunk #{i}"):
            st.write(s or "(rỗng)")

with st.expander("📜 Transcript (ghép)"):
    st.text_area("Transcript", value=full_text, height=350)
```

Người dùng thấy được cả ba tầng: transcript gốc → tóm tắt từng chunk → tóm tắt cuối. Nghi ngờ chỗ nào thì lần ngược về nguồn được.

Đây là cùng một nguyên tắc với `ToolTrace` (buổi 5) và "hiện lại câu SQL đã dùng" (buổi 6): **hệ thống AI phải cho người dùng kiểm chứng được**, chứ không chỉ ném ra một câu trả lời.

`st.columns([1.2, 1], gap="large")` chia layout theo tỉ lệ, `st.expander` gấp gọn nội dung dài.

### 6. Kiểm tra đầu vào trước, gọi API sau

```python
def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    return bool(re.search(r"(youtube\.com/watch\?v=|youtu\.be/)", url))
```

Validate URL bằng regex trước khi làm bất cứ việc gì tốn kém. Kết hợp với `st.error(...) + st.stop()` như buổi 3.

Từng khối được bọc `try/except` riêng với thông báo **cụ thể theo tình huống** thay vì một câu lỗi chung:

- Lỗi khi tải transcript → *"Có thể video không có subtitles public hoặc bị giới hạn."*
- Lỗi khi gọi model → *"có thể do model không truy cập được/không được cấp quyền, hoặc token sai."*

`st.exception(e)` in traceback đầy đủ bên dưới để debug.

## Đóng gói production — `docs/docker-compose.yaml`

Đây là file compose hoàn chỉnh nhất trong cả khoá (project `scholartube-edu`), gom lại mọi thứ về vận hành.

### 7. YAML anchor — khai báo một lần, dùng nhiều nơi

```yaml
x-service-defaults: &service-defaults
  init: true
  restart: unless-stopped
  security_opt:
    - no-new-privileges:true
  logging:
    driver: local
    options:
      max-size: "10m"
      max-file: "3"

services:
  backend:
    <<: *service-defaults
    ...
```

`x-` là prefix cho khối mở rộng (Docker Compose bỏ qua khi parse services). `&service-defaults` định nghĩa anchor, `<<: *service-defaults` merge vào service. Hết lặp lại cấu hình chung.

`logging` với `max-size: 10m` / `max-file: 3` là **log rotation** — không có nó thì log container có thể phình đến đầy ổ đĩa.

### 8. Bốn lớp làm cứng bảo mật container

| Cấu hình | Tác dụng |
| --- | --- |
| `no-new-privileges:true` | Process bên trong không leo thang được đặc quyền (chặn khai thác qua setuid) |
| `read_only: true` | **Toàn bộ filesystem của container là chỉ đọc** — mã độc chèn vào cũng không ghi được file |
| `tmpfs: /tmp:size=64m,mode=1777` | Cấp lại một vùng ghi tạm trong RAM, giới hạn 64 MB — vì `read_only` chặn cả `/tmp` mà app vẫn cần nó |
| `init: true` | Chạy init process, thu dọn zombie process và chuyển tín hiệu dừng đúng cách |

`read_only: true` + `tmpfs` là cặp đi liền: khoá hết rồi mở lại đúng chỗ cần thiết.

### 9. Biến bắt buộc vs biến có mặc định

```yaml
POSTGRES_DB: ${POSTGRES_DB:?Set POSTGRES_DB in .env.docker}       # thiếu → compose dừng, in đúng câu này
HF_MODEL: ${HF_MODEL:-Qwen/Qwen2.5-7B-Instruct}                   # thiếu → dùng mặc định
```

Đã gặp ở buổi 5, nhưng ở đây thông điệp lỗi được viết thành **hướng dẫn hành động** (`Set POSTGRES_DB in .env.docker`) thay vì chỉ báo thiếu. Chi tiết nhỏ, tiết kiệm rất nhiều thời gian cho người deploy.

Đáng chú ý: `SECRET_KEY` có mặc định `scholartube-local-secret-change-before-production` — tiện cho chạy local, nhưng đây là **khoá ký JWT**; deploy thật mà quên đổi là lỗ hổng nghiêm trọng. Nếu là mình sẽ đổi sang dạng `:?` bắt buộc như các biến DB.

### 10. Healthcheck của database dùng `psql` thay vì `pg_isready`

```yaml
test:
  - CMD-SHELL
  - >-
    PGPASSWORD="$${POSTGRES_PASSWORD}"
    psql --host=database --username="$${POSTGRES_USER}" --dbname="$${POSTGRES_DB}"
    --no-password --tuples-only --command="SELECT 1" >/dev/null
```

Buổi 5 và 7 dùng `pg_isready` — chỉ kiểm tra server có nhận kết nối không. Ở đây chạy hẳn `SELECT 1`, tức là kiểm tra **thật sự query được** với đúng user/database đó. Chặt hơn.

Chú ý `$${POSTGRES_PASSWORD}` — **hai dấu `$`**. Compose dùng `$` để nội suy biến của chính nó; `$$` để escape, giữ nguyên `${...}` cho shell bên trong container xử lý. Viết một `$` là compose ăn mất biến.

`>-` là folded block scalar của YAML: viết lệnh dài trên nhiều dòng, khi parse gộp lại thành một dòng.

### 11. Các biến HF trong cấu hình

```yaml
HF_TOKEN: ${HF_TOKEN:-}
HF_MODEL: ${HF_MODEL:-Qwen/Qwen2.5-7B-Instruct}
HF_INFERENCE_PROVIDER: ${HF_INFERENCE_PROVIDER:-auto}
HF_MAX_TOKENS: ${HF_MAX_TOKENS:-1200}
HF_TIMEOUT_SECONDS: ${HF_TIMEOUT_SECONDS:-120}
HF_REDUCE_BATCH_SIZE: ${HF_REDUCE_BATCH_SIZE:-8}
```

- **`HF_INFERENCE_PROVIDER: auto`** — HF định tuyến sang provider hạ tầng phù hợp, không cần chỉ định tay.
- **`HF_TIMEOUT_SECONDS: 120`** — model open-source chạy trên hạ tầng chia sẻ có thể phải chờ **cold start**, timeout mặc định của HTTP client thường quá ngắn.
- **`HF_REDUCE_BATCH_SIZE: 8`** — gộp 8 chunk summary mỗi lần reduce. Đây là lời giải cho vấn đề ở mục 4: video rất dài sinh ra hàng trăm chunk summary, nhét hết vào một prompt reduce sẽ vượt context window. Gộp theo batch 8 chính là **reduce nhiều tầng**.

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `docs/HuggingFace Youtube Summarizer` | Notebook đề bài — Streamlit + `YoutubeLoader` + `ChatHuggingFace`, các hàm `build_chat_model` và `load_youtube_transcript` để trống |
| `docs/docker-compose.yaml` | Stack `scholartube-edu`: Postgres 17 + backend + frontend, đã làm cứng bảo mật |

## Cách chạy

```bash
pip install streamlit langchain-huggingface langchain-community youtube-transcript-api
streamlit run app.py        # sau khi hoàn thiện notebook thành app.py
```

Cần **Hugging Face token** (`hf_...`) lấy từ trang Settings của tài khoản HF, nhập ở sidebar.

Toàn bộ stack:

```bash
cp .env.docker.example .env.docker
# điền POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / HF_TOKEN / SECRET_KEY
docker compose --env-file .env.docker up --build
# → http://localhost:3000
```

## Phần cần hoàn thiện

Hai hàm trong notebook mới chỉ có docstring:

- **`build_chat_model(hf_token, repo_id, max_new_tokens)`** — dựng `HuggingFaceEndpoint(repo_id=..., huggingfacehub_api_token=hf_token, max_new_tokens=...)` rồi bọc bằng `ChatHuggingFace(llm=...)`.
- **`load_youtube_transcript(url, preferred_langs, translate_to, chunk_seconds)`** — `YoutubeLoader.from_youtube_url(url, add_video_info=False, language=preferred_langs, translation=translate_to, transcript_format=TranscriptFormat.CHUNKS, chunk_size_seconds=chunk_seconds).load()`.

`summarize_docs_map_reduce()` và toàn bộ UI đã hoàn chỉnh sẵn.

## Tổng kết cả khoá

| Buổi | Nội dung | Thêm được điều gì |
| --- | --- | --- |
| 1 | OpenAI API + Streamlit | Gọi LLM, tự quản lý ngữ cảnh — API là stateless |
| 2 | LangChain + Groq | Trừu tượng hoá provider, LCEL, memory theo `session_id` |
| 3 | YouTube Summarizer | Document Loader, chunking, map-reduce cho văn bản dài |
| 4 | Structured Output | Pydantic schema, output validate được |
| 5 | Tool Calling | LLM **hành động** được: tool, vòng lặp agent, human-in-the-loop |
| 6 | SQL Agent | Toolkit dựng sẵn, agent tự khám phá schema, phòng thủ nhiều lớp |
| 7 | HuggingFace + Reasoning | Model open-source, tầng `transformers`, CoT / ToT / Self-Consistency |
| 8 | HF Inference + Docker | Đổi provider không đổi code, đóng gói production |

Ba sợi chỉ xuyên suốt:

1. **Quản lý ngữ cảnh** — tự append (b1) → `session_id` (b2) → lưu DB (b3) → agent state (b5–6).
2. **Kiểm soát output** — text thuần (b1–3) → schema (b4) → tool call (b5) → SQL có kiểm tra (b6) → chấm điểm tự động (b7).
3. **Minh bạch & an toàn** — chống bịa bằng prompt (b3) → trace + phê duyệt (b5) → read-only connection (b6) → container read-only (b8).
