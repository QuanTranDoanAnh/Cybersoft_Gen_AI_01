from fastapi import APIRouter, HTTPException, Query

from app.schemas.product import Product, ProductListResponse
from app.services import data_service

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    products = data_service.list_products(search, category)
    return {"products": products, "categories": ["Tất cả", *data_service.get_categories()]}


@router.get("/{product_id_or_slug}", response_model=Product)
def retrieve_product(product_id_or_slug: str):
    product = data_service.get_product(product_id_or_slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
