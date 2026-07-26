# Backend

FastAPI API cho CRM, task management, dashboard và OpenAI/LangChain Copilot.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

Nếu chưa có `OPENAI_API_KEY`, Copilot vẫn chạy ở chế độ demo cục bộ.

Swagger yêu cầu đăng nhập qua `POST /api/auth/login`. Session được lưu trong cookie `HttpOnly`.

## PostgreSQL

Backend ưu tiên PostgreSQL khi có đủ năm biến sau trong `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=orbit_user
DB_PASS=your_password
DATABASE=orbit
```

Database cần tồn tại trước. Khi backend khởi động, các bảng còn thiếu và dữ liệu demo ban đầu sẽ được tạo tự động. Nếu cả năm biến đều để trống, backend dùng SQLite local; nếu chỉ khai báo một phần, backend sẽ dừng và báo các biến còn thiếu.
