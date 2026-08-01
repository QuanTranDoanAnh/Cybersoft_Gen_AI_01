# Buổi 3 — Document Loader và tóm tắt văn bản dài (map-reduce)

Ngày học: 11/07/2026

## Mục tiêu

Hai buổi đầu, dữ liệu vào model chỉ là câu người dùng gõ. Buổi 3 mở rộng sang **đưa dữ liệu ngoài vào LLM**: tải transcript của một video YouTube rồi tóm tắt.

Bài toán cốt lõi: transcript của một video dài **vượt quá context window**. Lời giải là chia nhỏ → tóm tắt từng phần → tóm tắt các bản tóm tắt (**map-reduce summarization**).

File minh hoạ: `docs/Youtube Transcript Summarizations.ipynb` → bản hoàn chỉnh là `app.py`.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. Document Loader — cửa ngõ đưa dữ liệu ngoài vào LangChain

```python
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders.youtube import TranscriptFormat

loader = YoutubeLoader.from_youtube_url(
    url,
    add_video_info=add_info,
    transcript_format=TranscriptFormat.CHUNKS,
    chunk_size_seconds=120,
)
docs = loader.load()
```

`loader.load()` luôn trả về `list[Document]`. Mỗi `Document` có:

- `page_content` — nội dung text,
- `metadata` — thông tin nguồn (URL, tiêu đề, mốc thời gian của chunk…).

Đây là kiểu dữ liệu chuẩn của toàn hệ sinh thái LangChain: mọi loader (PDF, web, Wikipedia, arXiv…) đều trả về đúng dạng này, nên phần xử lý phía sau viết một lần dùng cho mọi nguồn.

Riêng loader này lấy **caption/phụ đề** sẵn có của video, không phải speech-to-text — nên video tắt caption sẽ không có transcript (app bắt trường hợp này và báo lỗi rõ ràng).

### 2. Chunking — chia transcript theo thời lượng

`TranscriptFormat.CHUNKS` + `chunk_size_seconds=120` cắt transcript thành các đoạn ~2 phút, mỗi đoạn là một `Document`. Không chia thì cả transcript là **một** `Document` khổng lồ, dễ vượt context window.

Đây là lần đầu gặp khái niệm chunking — cũng là nền tảng của RAG về sau.

### 3. Map-reduce summarization — hai tầng chain

**Tầng map** — tóm tắt từng chunk độc lập:

```python
chunk_chain = chunk_prompt | llm | StrOutputParser()

inputs = [{"instruction": chunk_instruction, "text": doc.page_content} for doc in docs]
chunk_summaries = chunk_chain.batch(inputs)
```

**Tầng reduce** — gộp các bản tóm tắt lại thành một bản cuối:

```python
combined = "\n\n".join(f"- Chunk {i+1}:\n{s}" for i, s in enumerate(chunk_summaries))

final_chain = final_prompts | llm | StrOutputParser()
return final_chain.invoke({
    "instruction": final_instruction,
    "format": final_format,
    "summaries": combined,
})
```

Ý tưởng: mỗi lần gọi LLM chỉ nhìn thấy một lượng text vừa phải, và bản tóm tắt của N chunk luôn ngắn hơn N chunk gốc rất nhiều.

### 4. `.batch()` — chạy nhiều input song song

`chunk_chain.batch(inputs)` gọi chain trên toàn bộ danh sách chunk, song song. Nhanh hơn hẳn vòng `for` gọi `.invoke()` lần lượt, vì các lượt gọi API độc lập nhau. Đây là điểm lợi của việc mọi thứ trong LCEL đều là Runnable.

### 5. `StrOutputParser` — bóc `.content` ngay trong chain

```python
chain = prompt | llm | StrOutputParser()
```

Không có parser thì chain trả về `AIMessage` và phải tự viết `.content`. Có parser thì chain trả thẳng `str` — quan trọng khi output của chain này là input của chain khác.

Đây là mắt xích thứ ba của pattern LCEL: **prompt → model → parser**.

### 6. Prompt engineering: tách "nội dung" khỏi "định dạng"

`summarize_docs()` xây prompt từ ba biến độc lập:

| Biến | Ý nghĩa | Nguồn |
| --- | --- | --- |
| `chunk_instruction` | Cách tóm tắt từng đoạn | Theo `lang` |
| `final_instruction` | Cách gộp các bản tóm tắt | Theo `lang` |
| `final_format` | Cấu trúc đầu ra (TL;DR / bullet / timeline / câu hỏi gợi mở) | Theo `detail` |

Người dùng đổi "Ngắn gọn / Vừa đủ / Chi tiết" trên UI thì thực chất là đổi `final_format` — cùng một chain, chỉ khác chỉ dẫn.

Đáng chú ý là các câu chống bịa đặt được viết thẳng vào prompt: *"giữ đúng ý, không bịa"*, *"Do not invent facts"*, *"ưu tiên tính chính xác"*.

### 7. `st.cache_data` — không tải lại transcript mỗi lần rerun

```python
@st.cache_data(show_spinner=False)
def load_transcript_docs(url, add_info, chunked, chunk_seconds):
    ...
```

Streamlit rerun toàn bộ script mỗi lần tương tác (đã học ở buổi 1). Với thao tác chậm/tốn tài nguyên như tải transcript, `@st.cache_data` cache theo bộ tham số đầu vào — đổi URL hoặc `chunk_size` mới tải lại. Nút "🧹 Xoá cache transcript" gọi `st.cache_data.clear()`.

### 8. Nhập API key từ UI thay vì `.env`

```python
groq_api_key = st.text_input("Groq API key", type="password")

def build_llm(api_key, model, temp):
    os.environ["GROQ_API_KEY"] = api_key   # ChatGroq đọc từ env
    return ChatGroq(model=model, temperature=temp)
```

`type="password"` để che ký tự. Cách này phù hợp khi app được deploy cho người khác dùng bằng key của chính họ.

### 9. Kiểm tra đầu vào trước khi gọi API

```python
if not groq_api_key:
    st.error("Bạn chưa nhập Groq API key.")
    st.stop()
```

`st.stop()` dừng script ngay tại đó. Nguyên tắc: chặn sớm ở phía client, đừng để một request thiếu dữ liệu đi tới API rồi mới lỗi.

## Bài tập đi kèm: ShopAI ver2 (fullstack)

Ngoài notebook, buổi 3 có một project hoàn chỉnh áp dụng lại memory của buổi 2 nhưng ở kiến trúc thật:

| Thư mục | Nội dung |
| --- | --- |
| `genai-shopai-ver2/` | Frontend Next.js + Tailwind: catalog, giỏ hàng, auth panel, chat widget |
| `genai-shopai-ver2-be/` | Backend FastAPI: router `auth` / `chat` / `conversations` / `orders` / `products`, Supabase (Postgres) |

Điểm đáng học trong `genai-shopai-ver2-be/app/services/chat_service.py`:

- **`PersistentChatMessageHistory`** — tự implement `BaseChatMessageHistory` để lịch sử nằm trong **database** thay vì RAM. Chỉ cần override `messages`, `add_messages()`, `clear()` là dùng được ngay với `RunnableWithMessageHistory`.
- **`session_id` ghép nhiều thông tin**: `f"{conversation_id}|{mode.value}"`, rồi tách ra trong `get_session_history()` — cách truyền thêm tham số qua một field string duy nhất.
- **`ChatMode.WITH_CONTEXT` / `WITHOUT_CONTEXT`** — chính là thí nghiệm "nhớ vs. không nhớ ngữ cảnh" của buổi 1, nhưng cho người dùng bật/tắt ngay trên UI.
- **System prompt được dựng động** từ dữ liệu thật (`build_system_prompt`): lọc sản phẩm liên quan, FAQ, đơn hàng được nhắc trong câu hỏi rồi nhét vào prompt. Đây là dạng RAG thủ công — tiền đề cho việc dùng vector store sau này.
- **`fallback_reply()`** — nhánh trả lời bằng rule khi không có API key hoặc LLM lỗi, để app không chết.

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `app.py` | YouTube Summarizer hoàn chỉnh (Streamlit + Groq) |
| `docs/Youtube Transcript Summarizations.ipynb` | Bản đề bài, các hàm để trống |
| `requirements.txt` | `streamlit`, `langchain`, `langchain-community`, `langchain-groq`, `youtube-transcript-api`, `pytube` |
| `genai-shopai-ver2/` | Frontend Next.js |
| `genai-shopai-ver2-be/` | Backend FastAPI + Supabase |

## Cách chạy

```bash
pip install -r requirements.txt
streamlit run app.py
# → nhập Groq API key ở sidebar, dán URL YouTube, bấm "🚀 Tóm tắt"
```

ShopAI ver2 xem hướng dẫn riêng trong `genai-shopai-ver2/README.md` và `genai-shopai-ver2-be/README.md`.
