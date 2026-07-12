from fastapi import APIRouter, HTTPException

from app.schemas.order import CreateOrderRequest, Order
from app.services import data_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/{order_id}", response_model=Order)
def retrieve_order(order_id: str):
    order = data_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("", response_model=Order)
def create_order(payload: CreateOrderRequest):
    try:
        return data_service.create_order(payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
