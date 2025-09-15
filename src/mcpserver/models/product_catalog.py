from pydantic import BaseModel


class ProductSearchRequest(BaseModel):
    query: str


class ProductByIdRequest(BaseModel):
    product_id: str


class ProductByCategoryRequest(BaseModel):
    category: str
