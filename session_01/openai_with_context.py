from openai import OpenAI
import os
from dotenv import load_dotenv
import streamlit as st
import json
from pathlib import Path

# Tải các biến môi trường từ file .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = "gpt-5-mini"
SYSTEM_PROMPT = "Bạn là một trợ lý AI hữu ích."
CHAT_HISTORY_FILE = Path(__file__).with_name("chat_history.json")
VALID_CHAT_ROLES = {"user", "assistant"}


def build_messages(chat_history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in chat_history:
        role = message.get("role")
        content = message.get("content")

        messages.append({"role": role, "content": content})
    return messages


# Hàm xử lý câu hỏi của user
def generate_bot_response(chat_history):
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            # Bên trong messages, vừa gửi đi req của user, vừa được dùng với những mục đích liên quan lưu trữ ngữ cảnh chat
            messages=build_messages(chat_history),
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Đã xảy ra lỗi: {str(e)}"


def save_chat_history():
    with CHAT_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(st.session_state.chat_history, f, ensure_ascii=False, indent=2)


def load_chat_history():
    try:
        with CHAT_HISTORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


st.set_page_config(layout="wide")

# Khởi tạo session state cho chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

# Thiết lập title
st.title("ChatGPT Clone bot")

# Hiển thị lịch sử chat
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Nhập câu hỏi của bạn...")

if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    save_chat_history()

    with st.chat_message("user"):
        st.markdown(prompt)

    # Lấy phản hồi từ chatbot
    response = generate_bot_response(st.session_state.chat_history)

    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    save_chat_history()


if st.button("Xoá lịch sử chat"):
    st.session_state.chat_history = []
    if CHAT_HISTORY_FILE.exists():
        CHAT_HISTORY_FILE.unlink()
    st.rerun()
