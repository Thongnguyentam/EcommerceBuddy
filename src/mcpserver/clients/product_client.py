import grpc
from typing import Optional, List

# Use the local protobuf files we copied to mcpserver directory  
import demo_pb2
import demo_pb2_grpc


class ProductCatalogServiceClient:
    """
    Client for ProductCatalogService gRPC API.
    
    Responsibilities:
    - Manage gRPC channel lifecycle  
    - Provide ergonomic, typed methods for product operations
    - Keep network/serialization details out of tool logic
    """
    
    def __init__(self, host: str = "productcatalogservice:3550", insecure: bool = True) -> None:
        self._host = host
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[demo_pb2_grpc.ProductCatalogServiceStub] = None
        self._insecure = insecure
    
    def connect(self) -> None:
        if self._channel is None:
            self._channel = grpc.insecure_channel(self._host) if self._insecure else grpc.secure_channel(self._host, grpc.ssl_channel_credentials())
            self._stub = demo_pb2_grpc.ProductCatalogServiceStub(self._channel)
    
    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
    
    # Product catalog operations
    def list_products(self) -> demo_pb2.ListProductsResponse:
        """Get all products from the catalog."""
        self._ensure_connected()
        request = demo_pb2.Empty()
        return self._stub.ListProducts(request)  # type: ignore[arg-type]
    
    def get_product(self, product_id: str) -> demo_pb2.Product:
        """Get a specific product by ID."""
        self._ensure_connected()
        request = demo_pb2.GetProductRequest(id=product_id)
        return self._stub.GetProduct(request)  # type: ignore[arg-type]
    
    def search_products(self, query: str) -> demo_pb2.SearchProductsResponse:
        """Search products by query string."""
        self._ensure_connected()
        request = demo_pb2.SearchProductsRequest(query=query)
        return self._stub.SearchProducts(request)  # type: ignore[arg-type]
    
    def _ensure_connected(self) -> None:
        if self._stub is None:
            self.connect()
