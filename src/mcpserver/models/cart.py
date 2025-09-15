from pydantic import BaseModel


class AddToCartRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int


class CartRequest(BaseModel):
    user_id: str
