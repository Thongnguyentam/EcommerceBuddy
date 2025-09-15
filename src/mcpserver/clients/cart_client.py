import grpc
from typing import Optional

# Use the local protobuf files we copied to mcpserver directory
import demo_pb2
import demo_pb2_grpc

# Client stub (you’re using it): CartServiceStub
# Server stub/servicer: CartServiceServicer (for implementing the server)
class CartServiceClient:
	"""

	Responsibilities:
	- Manage gRPC channel lifecycle
	- Provide ergonomic, typed methods for cart operations
	- Keep network/serialization details out of tool logic
	"""

	def __init__(self, host: str = "cartservice:7070", insecure: bool = True) -> None:
		self._host = host
		self._channel: Optional[grpc.Channel] = None
		self._stub: Optional[demo_pb2_grpc.CartServiceStub] = None
		self._insecure = insecure

	def connect(self) -> None:
		if self._channel is None:
			self._channel = grpc.insecure_channel(self._host) if self._insecure else grpc.secure_channel(self._host, grpc.ssl_channel_credentials())
			self._stub = demo_pb2_grpc.CartServiceStub(self._channel)

	def close(self) -> None:
		if self._channel is not None:
			self._channel.close()
			self._channel = None
			self._stub = None

	# Synchronous methods for simplicity; can be adapted to async if needed
	def add_item(self, user_id: str, product_id: str, quantity: int) -> demo_pb2.Empty:
		self._ensure_connected()
		request = demo_pb2.AddItemRequest(
			user_id=user_id,
			item=demo_pb2.CartItem(product_id=product_id, quantity=quantity),
		)
		return self._stub.AddItem(request)  # type: ignore[arg-type]

	def get_cart(self, user_id: str) -> demo_pb2.Cart:
		self._ensure_connected()
		request = demo_pb2.GetCartRequest(user_id=user_id)
		return self._stub.GetCart(request)  # type: ignore[arg-type]

	def empty_cart(self, user_id: str) -> demo_pb2.Empty:
		self._ensure_connected()
		request = demo_pb2.EmptyCartRequest(user_id=user_id)
		return self._stub.EmptyCart(request)  # type: ignore[arg-type]

	def _ensure_connected(self) -> None:
		if self._stub is None:
			self.connect()

