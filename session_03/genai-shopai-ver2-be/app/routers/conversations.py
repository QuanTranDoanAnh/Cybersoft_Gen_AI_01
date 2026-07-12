from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.conversation import ConversationDetail, ConversationListResponse, ConversationSummary, UpdateConversationRequest
from app.services import account_service, auth_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
def list_conversations(user: dict = Depends(auth_service.require_user)):
    return ConversationListResponse(conversations=account_service.list_conversations(user["id"]))


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, user: dict = Depends(auth_service.require_user)):
    conversation = account_service.get_conversation(user["id"], conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện.")
    messages = account_service.list_messages(conversation_id)
    return ConversationDetail(**conversation, messages=messages)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def update_conversation(conversation_id: str, payload: UpdateConversationRequest, user: dict = Depends(auth_service.require_user)):
    conversation = account_service.update_conversation(user["id"], conversation_id, title=payload.title, mode=payload.mode)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện.")
    return ConversationSummary(**conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: dict = Depends(auth_service.require_user)):
    deleted = account_service.delete_conversation(user["id"], conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
