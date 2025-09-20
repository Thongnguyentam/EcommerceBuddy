from pydantic import BaseModel
from typing import Optional


class ProductSearchRequest(BaseModel):
    query: str


class ProductByIdRequest(BaseModel):
    product_id: str


class ProductByCategoryRequest(BaseModel):
    category: str


class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
