from pydantic import BaseModel, Field


class CartItemInput(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class CreateOrderRequest(BaseModel):
    customer_name: str = Field(min_length=2)
    phone: str = Field(min_length=8)
    address: str = Field(min_length=8)
    items: list[CartItemInput]


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price: int


class Order(BaseModel):
    id: str
    customer_name: str
    phone: str
    address: str
    status: str
    total_amount: int
    items: list[OrderItem]
    created_at: str

