# Frontend

Next.js TypeScript dashboard cho AI Business Copilot.

```bash
npm install
cp .env.example .env.local
npm run dev
```

Mở http://localhost:3000. Frontend mặc định proxy `/api` tới backend ở http://localhost:8000.

Khi chạy bằng Docker Compose, proxy tự chuyển sang service `backend` trong mạng nội bộ Docker.
