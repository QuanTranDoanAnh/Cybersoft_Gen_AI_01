# Buổi 1 — Gọi OpenAI API & xây dựng chatbot có ngữ cảnh

Ngày học: 04/07/2026

## Mục tiêu

Từ đoạn code minh hoạ trong `docs/Tài nguyên buổi 1`, buổi học đi qua 3 bước tăng dần độ hoàn thiện của một "ChatGPT Clone bot":

1. Gọi OpenAI API thuần bằng Python (chạy trong terminal).
2. Bọc lời gọi API bằng giao diện web Streamlit — nhưng **chưa nhớ ngữ cảnh**.
3. Bổ sung lịch sử hội thoại (chat history) để bot **nhớ ngữ cảnh**, kèm lưu trữ xuống file.

## Nội dung lý thuyết rút ra từ đoạn mã

### 1. Client và API key

```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

- `OpenAI(...)` tạo một client — object dùng lại cho mọi request, giữ thông tin xác thực.
- API key **không hardcode trong source**: đặt trong file `.env`, nạp bằng `load_dotenv()` của `python-dotenv` rồi đọc qua `os.getenv`. File `.env` phải được gitignore.

### 2. Chat Completions và cấu trúc `messages`

```python
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "Bạn là một trợ lý AI hữu ích."},
        {"role": "user", "content": user_question},
    ],
)
print(response.choices[0].message.content)
```

- Mỗi phần tử trong `messages` là một cặp `role` + `content`.
- Ba vai trò:
  - `system` — chỉ dẫn nền, định hình tính cách/nhiệm vụ của bot. Luôn đặt đầu tiên.
  - `user` — câu hỏi của người dùng.
  - `assistant` — câu trả lời model đã sinh ra ở lượt trước.
- Nội dung trả lời nằm ở `response.choices[0].message.content`.
- Gọi API luôn có thể lỗi (mạng, hết quota, sai key) nên bọc trong `try/except`:

```python
except Exception as e:
    return f"Đã xảy ra lỗi: {str(e)}"
```

### 3. Điểm mấu chốt: **API của LLM là stateless**

Đây là bài học trọng tâm của buổi. Server OpenAI **không tự nhớ** các lượt chat trước. Nếu mỗi lần chỉ gửi đúng câu hỏi hiện tại:

```python
messages=[
    {"role": "system", ...},
    {"role": "user", "content": user_input},   # chỉ có câu hỏi mới nhất
]
```

thì hỏi "Tên tôi là Quân" rồi hỏi tiếp "Tôi tên gì?" → bot không trả lời được.

Muốn bot nhớ, **phía client phải tự gom toàn bộ lịch sử và gửi lại kèm mỗi request**:

```python
def build_messages(chat_history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in chat_history:
        messages.append({
            "role": message.get("role"),
            "content": message.get("content"),
        })
    return messages
```

Hệ quả cần lưu ý: hội thoại càng dài thì `messages` càng lớn → tốn token và chi phí, và cuối cùng sẽ chạm giới hạn context window.

### 4. Giao diện chat bằng Streamlit

| API | Vai trò |
| --- | --- |
| `st.set_page_config(layout="wide")` | Cấu hình trang, phải gọi trước mọi lệnh Streamlit khác |
| `st.title(...)` | Tiêu đề ứng dụng |
| `st.chat_input(...)` | Ô nhập kiểu chat ghim dưới đáy trang; trả `None` khi người dùng chưa gửi |
| `st.chat_message(role)` | Context manager vẽ bong bóng chat theo vai trò `user` / `assistant` |
| `st.markdown(...)` | Render nội dung có định dạng bên trong bong bóng |
| `st.button(...)` + `st.rerun()` | Nút "Xoá lịch sử chat" và ép chạy lại script để cập nhật UI |

### 5. `st.session_state` — nơi giữ ngữ cảnh giữa các lần rerun

Streamlit **chạy lại toàn bộ file** mỗi khi người dùng tương tác, nên biến Python thường sẽ bị reset. `st.session_state` là bộ nhớ tồn tại xuyên suốt phiên làm việc:

```python
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()
```

Vòng lặp hiển thị lại toàn bộ lịch sử ở đầu mỗi lần rerun chính là lý do khung chat không bị mất nội dung cũ.

### 6. Lưu lịch sử xuống file JSON

`session_state` mất khi đóng tab, nên lịch sử được ghi xuống `chat_history.json`:

- `Path(__file__).with_name("chat_history.json")` — lấy đường dẫn cạnh file script, không phụ thuộc thư mục đang chạy.
- `json.dump(..., ensure_ascii=False, indent=2)` — `ensure_ascii=False` để tiếng Việt không bị escape thành `\uXXXX`.
- `load_chat_history()` bắt `FileNotFoundError` và trả `[]` cho lần chạy đầu tiên.
- Nút xoá: reset `session_state` + `CHAT_HISTORY_FILE.unlink()` + `st.rerun()`.

### 7. Luồng xử lý một lượt chat hoàn chỉnh

```
người dùng gửi prompt
   → append {"role": "user"} vào chat_history → lưu file
   → hiển thị bong bóng user
   → build_messages(chat_history) → gọi API → nhận response
   → hiển thị bong bóng assistant
   → append {"role": "assistant"} vào chat_history → lưu file
```

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `intro_to_openai.py` | Gọi API cơ bản, nhập câu hỏi bằng `input()`, in kết quả ra terminal |
| `openai_with_ui.py` | Bọc lời gọi API bằng Streamlit — **không nhớ ngữ cảnh** |
| `openai_with_context.py` | Bản đầy đủ: chat history + `session_state` + lưu JSON + nút xoá |
| `chat_history.json` | Lịch sử hội thoại được sinh ra khi chạy |
| `requirements.txt` | `openai`, `streamlit`, `python-dotenv` |
| `docs/Tài nguyên buổi 1` | Notebook code mẫu của giảng viên |
| `genai-shopai/`, `genai-shopai-be/` | Project demo tham khảo (Next.js frontend + backend) |

## Cách chạy

```bash
pip install -r requirements.txt

# tạo file .env với nội dung:
# OPENAI_API_KEY=sk-...

python intro_to_openai.py            # bản terminal
streamlit run openai_with_ui.py      # bản UI, không nhớ ngữ cảnh
streamlit run openai_with_context.py # bản đầy đủ, có nhớ ngữ cảnh
```

## Ghi chú

`intro_to_openai.py` hiện đang hardcode API key ngay trong source. Nên chuyển sang đọc từ `.env` như hai file còn lại, và thu hồi (revoke) key đó vì nó đã nằm trong lịch sử git.
