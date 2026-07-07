from openai import OpenAI
import os
from dotenv import load_dotenv
import streamlit as st

# Tải các biến môi trường từ file .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Hàm xử lý câu hỏi của user
def generate_bot_response(user_input: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            # Bên trong messages, vừa gửi đi req của user, vừa được dùng với những mục đích liên quan lưu trữ ngữ cảnh chat
            messages=[
                {"role": "system", "content": "Đây là một trợ lý AI"},
                {"role": "user", "content": user_input},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Đã xảy ra lỗi: {str(e)}"


st.set_page_config(layout="wide")
# Thiết lập title
st.title("ChatGPT Clone bot")

prompt = st.chat_input("Nhập câu hỏi của bạn...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    # Lấy phản hồi từ chatbot
    response = generate_bot_response(prompt)

    with st.chat_message("assistant"):
        st.markdown(response)
