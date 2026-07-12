import os
import re
import streamlit as st

from langchain_groq import ChatGroq
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders.youtube import TranscriptFormat

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


st.set_page_config(
    page_title="YouTube Summarizer (Groq + LangChain)", page_icon="🎬", layout="wide"
)

st.title("🎬 Tóm tắt YouTube bằng Transcript + ChatGroq")
st.caption(
    "Nhập Groq API key → dán YouTube URL → tải transcript bằng YoutubeLoader → tóm tắt bằng ChatGroq."
)

with st.sidebar:
    st.header("Cấu hình")
    groq_api_key = st.text_input(
        "Groq API key", type="password", help="Sẽ được set vào env GROQ_API_KEY."
    )
    model_name = st.text_input("Model", value="qwen/qwen3-32b")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

    st.divider()
    st.subheader("Transcript loader")
    add_video_info = st.checkbox("Thêm video info (cần pytube)", value=False)
    use_chunked_transcript = st.checkbox(
        "Lấy transcript dạng chunks (khuyến nghị)", value=True
    )
    chunk_size_seconds = st.number_input(
        "Chunk size (seconds)", min_value=15, max_value=600, value=120, step=15
    )

    st.divider()
    st.subheader("Đầu ra")
    output_lang = st.selectbox("Ngôn ngữ tóm tắt", ["Tiếng Việt", "English"], index=0)
    detail_level = st.selectbox(
        "Mức độ chi tiết", ["Ngắn gọn", "Vừa đủ", "Chi tiết"], index=1
    )

youtube_url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=QsYGlZkevEg",
)

col1, col2 = st.columns([1, 1])
with col1:
    run_btn = st.button("🚀 Tóm tắt", type="primary", use_container_width=True)
with col2:
    st.button(
        "🧹 Xoá cache transcript",
        use_container_width=True,
        on_click=lambda: st.cache_data.clear(),
    )


def _normalize_youtube_url(url: str) -> str:
    """Basic normalize to avoid common paste issues."""
    url = (url or "").strip()
    url = re.sub(r"\s+", "", url)
    return url


@st.cache_data(show_spinner=False)
def load_transcript_docs(url: str, add_info: bool, chunked: bool, chunk_seconds: int):
    """
    Load transcript documents via LangChain YoutubeLoader.
    Docs:
      - YoutubeLoader.from_youtube_url(url, add_video_info=...)
      - transcript_format=TranscriptFormat.CHUNKS, chunk_size_seconds=...
    """
    # Code tiếp ở đây
    if chunked:
        loader = YoutubeLoader.from_youtube_url(
            url,
            add_video_info=add_info,
            transcript_format=TranscriptFormat.CHUNKS,
            chunk_size_seconds=int(chunk_seconds),
        )
    else:
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=add_info)
    return loader.load()


def build_llm(api_key: str, model: str, temp: float) -> ChatGroq:
    os.environ["GROQ_API_KEY"] = (
        api_key  # LangChain Groq expects GROQ_API_KEY in env by default.  :contentReference[oaicite:2]{index=2}
    )
    return ChatGroq(model=model, temperature=temp)


def summarize_docs(llm: ChatGroq, docs, lang: str, detail: str) -> str:
    # Prompts
    if lang == "Tiếng Việt":
        chunk_instruction = "Tóm tắt đoạn transcript sau thành 4-6 gạch đầu dòng, giữ đúng ý, không bịa."
        final_instruction = (
            "Tổng hợp các tóm tắt đoạn thành một bản tóm tắt mạch lạc bằng tiếng Việt."
        )
    else:
        chunk_instruction = "Summarize the following transcript chunk into 4-6 bullet points. Do not invent facts."
        final_instruction = (
            "Combine chunk summaries into a coherent final summary in English."
        )

    if detail == "Ngắn gọn":
        final_format = (
            "Đầu ra gồm:\n"
            "1) TL;DR (2-3 câu)\n"
            "2) 5 ý chính (bullet)\n"
            "3) Kết luận (1 câu)\n"
            if lang == "Tiếng Việt"
            else "Output:\n1) TL;DR (2-3 sentences)\n2) 5 key points (bullets)\n3) Conclusion (1 sentence)\n"
        )
    elif detail == "Chi tiết":
        final_format = (
            "Đầu ra gồm:\n"
            "1) TL;DR (3-5 câu)\n"
            "2) Dàn ý theo mục (headings + bullet)\n"
            "3) Các thuật ngữ/khái niệm quan trọng\n"
            "4) Nếu có thể: timeline/diễn tiến theo thời gian\n"
            "5) 3 câu hỏi gợi mở để học sâu hơn\n"
            if lang == "Tiếng Việt"
            else "Output:\n"
            "1) TL;DR (3-5 sentences)\n"
            "2) Structured outline (headings + bullets)\n"
            "3) Key terms/concepts\n"
            "4) If possible: timeline\n"
            "5) 3 follow-up questions\n"
        )
    else:
        final_format = (
            "Đầu ra gồm:\n"
            "1) TL;DR (3-4 câu)\n"
            "2) Ý chính (8-12 bullet)\n"
            "3) Trích ý/quote ngắn (nếu có) + giải thích\n"
            if lang == "Tiếng Việt"
            else "Output:\n1) TL;DR (3-4 sentences)\n2) Main points (8-12 bullets)\n3) Short notable quote/idea (if any) + explanation\n"
        )

    chunk_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Bạn là trợ lý tóm tắt trung thực và rõ ràng."
                if lang == "Tiếng Việt"
                else "You are a precise and faithful summarizer.",
            ),
            ("human", "{instruction}\n\nTRANSCRIPT CHUNK:\n{text}"),
        ]
    )
    # Code tiếp ở đây
    chunk_chain = chunk_prompt | llm | StrOutputParser()

    inputs = [
        {"instruction": chunk_instruction, "text": doc.page_content} for doc in docs
    ]
    chunk_summaries = chunk_chain.batch(inputs)

    combined = "\n\n".join(
        [f"- Chunk {i + 1}:\n{summary}" for i, summary in enumerate(chunk_summaries)]
    )
    final_prompts = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Bạn là trợ lý tóm tắt cấp cao, ưu tiên tính chính xác."
                if lang == "Tiếng Việt"
                else "You are a senior summarization assistant, prioritize accuracy.",
            ),
            ("human", "{instruction}\n\n{format}\n\nCHUNK SUMMARIES:\n{summaries}"),
        ]
    )

    final_chain = final_prompts | llm | StrOutputParser()

    return final_chain.invoke(
        {
            "instruction": final_instruction,
            "format": final_format,
            "summaries": combined,
        }
    )


if run_btn:
    url = _normalize_youtube_url(youtube_url)

    if not groq_api_key:
        st.error("Bạn chưa nhập Groq API key.")
        st.stop()
    if not url:
        st.error("Bạn chưa dán YouTube URL.")
        st.stop()

    try:
        with st.spinner("Đang tải transcript từ YouTube..."):
            docs = load_transcript_docs(
                url, add_video_info, use_chunked_transcript, int(chunk_size_seconds)
            )

        if not docs:
            st.error(
                "Không lấy được transcript (video có thể tắt captions / không có transcript / bị giới hạn)."
            )
            st.stop()

        # Show metadata
        with st.expander("📄 Xem transcript metadata / số chunk", expanded=False):
            st.write(f"Số Document: **{len(docs)}**")
            st.write("Metadata mẫu (doc đầu tiên):")
            st.json(docs[0].metadata)

        llm = build_llm(groq_api_key, model_name, temperature)

        with st.spinner("Đang tóm tắt bằng ChatGroq..."):
            summary = summarize_docs(llm, docs, output_lang, detail_level)

        st.subheader("✅ Tóm tắt")
        st.markdown(summary)

        with st.expander("🧩 Transcript thô (preview)", expanded=False):
            preview = "\n\n".join([d.page_content[:1500] for d in docs[:3]])
            st.text(preview)

    except Exception as e:
        st.exception(e)
