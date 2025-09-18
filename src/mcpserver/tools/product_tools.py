from typing import Dict, Any, List
from clients.product_client import ProductCatalogServiceClient
from genproto import demo_pb2


class ProductTools:
    """
    High-level tools for product catalog operations.
    
    These methods provide business logic, validation, and user-friendly responses
    for MCP (Model Context Protocol) integration.
    """
    
    def __init__(self, client: ProductCatalogServiceClient | None = None) -> None:
        self._client = client or ProductCatalogServiceClient()
    
    def list_all_products(self) -> Dict[str, Any]:
        """
        Get all products from the catalog.
        
        Returns:
            Dict with status, products list, and count
        """
        try:
            response = self._client.list_products()
            
            products = []
            for product in response.products:
                products.append(self._format_product(product))
            
            return {
                "status": "ok",
                "products": products,
                "total_count": len(products),
                "message": f"Retrieved {len(products)} products from catalog"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to list products: {str(e)}",
                "products": [],
                "total_count": 0
            }
    
    def get_product_by_id(self, product_id: str) -> Dict[str, Any]:
        """
        Get a specific product by its ID.
        
        Args:
            product_id: The product ID to look up
            
        Returns:
            Dict with status and product details
        """
        if not product_id or not product_id.strip():
            return {
                "status": "error",
                "message": "Product ID cannot be empty",
                "product": None
            }
        
        try:
            product = self._client.get_product(product_id.strip())
            
            return {
                "status": "ok",
                "product": self._format_product(product),
                "message": f"Found product: {product.name}"
            }
            
        except Exception as e:
            # gRPC returns NOT_FOUND for missing products
            if "NOT_FOUND" in str(e) or "not found" in str(e).lower():
                return {
                    "status": "not_found",
                    "message": f"Product with ID '{product_id}' not found",
                    "product": None
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get product: {str(e)}",
                    "product": None
                }
    
    def search_products(self, query: str) -> Dict[str, Any]:
        """
        Search for products by name, description, or category.
        
        Args:
            query: Search terms
            
        Returns:
            Dict with status, matching products, and count
        """
        if not query or not query.strip():
            return {
                "status": "error",
                "message": "Search query cannot be empty",
                "products": [],
                "total_count": 0
            }
        
        try:
            response = self._client.search_products(query.strip())
            
            products = []
            for product in response.results:
                products.append(self._format_product(product))
            
            return {
                "status": "ok",
                "products": products,
                "total_count": len(products),
                "query": query.strip(),
                "message": f"Found {len(products)} products matching '{query}'"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to search products: {str(e)}",
                "products": [],
                "total_count": 0,
                "query": query.strip()
            }
    
    def get_products_by_category(self, category: str) -> Dict[str, Any]:
        """
        Get all products in a specific category.
        
        Args:
            category: Category name to filter by
            
        Returns:
            Dict with status, filtered products, and count
        """
        if not category or not category.strip():
            return {
                "status": "error",
                "message": "Category cannot be empty",
                "products": [],
                "total_count": 0
            }
        
        try:
            # Get all products first, then filter by category
            response = self._client.list_products()
            category_lower = category.strip().lower()
            
            matching_products = []
            for product in response.products:
                # Check if any of the product's categories match
                product_categories = [cat.lower() for cat in product.categories]
                if category_lower in product_categories:
                    matching_products.append(self._format_product(product))
            
            return {
                "status": "ok",
                "products": matching_products,
                "total_count": len(matching_products),
                "category": category.strip(),
                "message": f"Found {len(matching_products)} products in category '{category}'"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get products by category: {str(e)}",
                "products": [],
                "total_count": 0,
                "category": category.strip()
            }
    
    def _format_product(self, product: demo_pb2.Product) -> Dict[str, Any]:
        """
        Convert a protobuf Product to a user-friendly dict.
        
        Args:
            product: The protobuf Product object
            
        Returns:
            Dict representation of the product
        """
        # Format the price from Money object
        price_info = None
        if product.price_usd:
            # Convert nanos to decimal (nanos are 10^-9, so divide by 1 billion)
            total_cents = product.price_usd.nanos // 10_000_000  # Convert nanos to cents  
            dollars = product.price_usd.units
            cents = total_cents
            
            price_info = {
                "currency": product.price_usd.currency_code,
                "units": dollars,
                "nanos": product.price_usd.nanos,
                "formatted": f"${dollars}.{cents:02d}"  # e.g., "$19.99"
            }
        
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "picture": product.picture,
            "price": price_info,
            "categories": list(product.categories)  # Convert from protobuf repeated field
        }
