from pydantic import BaseModel


class Product(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    price: int
    original_price: int | None = None
    category: str
    rating: float
    sold_count: int
    stock: int
    image_url: str
    variants: list[str] = []
    tags: list[str] = []


class ProductListResponse(BaseModel):
    products: list[Product]
    categories: list[str]

