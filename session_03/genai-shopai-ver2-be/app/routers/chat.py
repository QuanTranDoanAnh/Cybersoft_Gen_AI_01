from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
from app.services import auth_service
from app.services.chat_service import handle_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: dict = Depends(auth_service.require_user)):
    try:
        return handle_chat(payload, user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
