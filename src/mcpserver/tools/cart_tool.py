from typing import Dict, Any

from clients.cart_client import CartServiceClient


class CartTools:
	"""MCP-exposed cart operations.

	This class provides simple, validated methods that MCP can expose as tools.
	It delegates actual service calls to the gRPC `CartServiceClient`.
	"""

	def __init__(self, client: CartServiceClient | None = None) -> None:
		self._client = client or CartServiceClient()

	def add_to_cart(self, user_id: str, product_id: str, quantity: int) -> Dict[str, Any]:
		self._validate_user_id(user_id)
		self._validate_product_id(product_id)
		self._validate_quantity(quantity)

		resp = self._client.add_item(user_id=user_id, product_id=product_id, quantity=quantity)
		return {
			"status": "ok",
			"message": f"Added {quantity} of product '{product_id}' to cart for user '{user_id}'.",
		}

	def get_cart_contents(self, user_id: str) -> Dict[str, Any]:
		self._validate_user_id(user_id)
		cart = self._client.get_cart(user_id=user_id)
		items = [
			{"product_id": i.product_id, "quantity": i.quantity}
			for i in cart.items
		]
		return {
			"status": "ok",
			"user_id": user_id,
			"items": items,
			"total_items": sum(i["quantity"] for i in items),
		}

	def clear_cart(self, user_id: str) -> Dict[str, Any]:
		self._validate_user_id(user_id)
		self._client.empty_cart(user_id=user_id)
		return {"status": "ok", "message": f"Cleared cart for user '{user_id}'."}

	def _validate_user_id(self, user_id: str) -> None:
		if not user_id or not isinstance(user_id, str):
			raise ValueError("user_id must be a non-empty string")

	def _validate_product_id(self, product_id: str) -> None:
		if not product_id or not isinstance(product_id, str):
			raise ValueError("product_id must be a non-empty string")

	def _validate_quantity(self, quantity: int) -> None:
		if not isinstance(quantity, int) or quantity <= 0:
			raise ValueError("quantity must be a positive integer")
