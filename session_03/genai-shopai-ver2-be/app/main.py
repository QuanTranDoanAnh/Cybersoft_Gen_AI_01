import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chat, conversations, orders, products
from app.services.data_service import postgres_enabled

load_dotenv()

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(
    title="ShopAI Assistant API",
    description="FastAPI backend for a Shopee-like ecommerce demo with an AI customer support bot.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(orders.router)
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "data_source": "postgres" if postgres_enabled() else "mock",
    }
