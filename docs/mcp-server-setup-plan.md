# MCP Server Setup Plan for Online Boutique
## Model Context Protocol Servers for Cart Service & Product Catalog

### 🎯 **Objective**
Create MCP servers that allow AI assistants (like Claude, ChatGPT, etc.) to interact with:
- **Cart Service**: Add/remove items, view cart contents, manage user sessions
- **Product Catalog Service**: Search products, get product details, browse categories

### 📋 **MCP Server Overview**
- **MCP (Model Context Protocol)** enables AI assistants to connect to external tools and data sources
- **MCP Servers** expose specific APIs that AI models can call
- **Online Boutique Integration**: Bridge between AI assistants and microservices

---

## 🏗️ **Architecture Plan**

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   AI Assistant  │    │   MCP Server     │    │  Online Boutique  │
│  (Claude/GPT)   │◄──►│   (FastAPI)      │◄──►│   Microservices   │
│                 │    │                  │    │                   │
│ • Natural Lang  │    │ • Cart Tools     │    │ • cartservice     │
│ • Tool Calling  │    │ • Product Tools  │    │ • productcatalog  │
│ • Conversations │    │ • Auth & Validation│   │ • Cloud SQL       │
└─────────────────┘    └──────────────────┘    └───────────────────┘
```

---

## 🛠️ **Implementation Plan**

### **Phase 1: MCP Server Infrastructure**

#### **1.1 Create MCP Server Microservice**
```bash
# New microservice structure
src/mcpserver/
├── main.py              # FastAPI server entry point
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container definition
├── config.py           # Configuration management
├── tools/
│   ├── __init__.py
│   ├── cart_tools.py   # Cart-related MCP tools
│   └── product_tools.py # Product-related MCP tools
├── clients/
│   ├── __init__.py
│   ├── cart_client.py  # gRPC client for cartservice
│   └── product_client.py # gRPC client for productcatalog
└── auth/
    ├── __init__.py
    └── session_manager.py # User session management
```

#### **1.2 Kubernetes Deployment**
```yaml
# kustomize/components/mcpserver/
├── deployment.yaml     # MCP server deployment
├── service.yaml       # Internal service exposure
├── configmap.yaml     # Configuration
└── kustomization.yaml # Kustomize component
```

### **Phase 2: MCP Tools Implementation**

#### **2.1 Cart Service Tools**
```python
# tools/cart_tools.py
class CartTools:
    async def add_to_cart(self, user_id: str, product_id: str, quantity: int)
    async def remove_from_cart(self, user_id: str, product_id: str)
    async def get_cart_contents(self, user_id: str)
    async def clear_cart(self, user_id: str)
    async def update_quantity(self, user_id: str, product_id: str, quantity: int)
```

#### **2.2 Product Catalog Tools**
```python
# tools/product_tools.py
class ProductTools:
    async def search_products(self, query: str, limit: int = 10)
    async def get_product_details(self, product_id: str)
    async def list_products_by_category(self, category: str)
    async def get_all_categories(self)
    async def get_featured_products(self, limit: int = 5)
```

### **Phase 3: Integration Layer**

#### **3.1 gRPC Client Setup**
```python
# clients/cart_client.py
import grpc
from protos import demo_pb2_grpc, demo_pb2

class CartServiceClient:
    def __init__(self, service_host="cartservice:7070"):
        self.channel = grpc.insecure_channel(service_host)
        self.stub = demo_pb2_grpc.CartServiceStub(self.channel)
    
    async def add_item(self, user_id, product_id, quantity):
        request = demo_pb2.AddItemRequest(
            user_id=user_id,
            item=demo_pb2.CartItem(product_id=product_id, quantity=quantity)
        )
        return await self.stub.AddItem(request)
```

#### **3.2 Product Catalog Client**
```python
# clients/product_client.py
class ProductCatalogClient:
    def __init__(self, service_host="productcatalogservice:3550"):
        self.channel = grpc.insecure_channel(service_host)
        self.stub = demo_pb2_grpc.ProductCatalogServiceStub(self.channel)
    
    async def list_products(self):
        request = demo_pb2.Empty()
        return await self.stub.ListProducts(request)
```

### **Phase 4: FastAPI MCP Server**

#### **4.1 Main Server**
```python
# main.py
from fastapi import FastAPI
from mcp import Server, RequestContext
from tools.cart_tools import CartTools
from tools.product_tools import ProductTools

app = FastAPI(title="Online Boutique MCP Server")
mcp_server = Server("online-boutique")

# Register tools
cart_tools = CartTools()
product_tools = ProductTools()

@mcp_server.tool()
async def add_to_cart(context: RequestContext, user_id: str, product_id: str, quantity: int):
    """Add item to user's shopping cart"""
    return await cart_tools.add_to_cart(user_id, product_id, quantity)

@mcp_server.tool()
async def search_products(context: RequestContext, query: str, limit: int = 10):
    """Search for products by name or description"""
    return await product_tools.search_products(query, limit)

# More tools...
```

---

## 🚀 **Deployment Strategy**

### **Option 1: Separate Namespace (Recommended)**
```bash
# Create dedicated namespace for MCP tools
kubectl create namespace mcp-tools

# Deploy MCP server
kubectl apply -f kustomize/components/mcpserver/ -n mcp-tools
```

### **Option 2: Same Namespace with Network Policies**
```bash
# Deploy in default namespace with network isolation
kubectl apply -f kustomize/components/mcpserver/
```

### **Option 3: External Cluster**
```bash
# Deploy MCP server in separate cluster for security
# Connect via service mesh or VPN
```

---

## 🔒 **Security & Access Control**

### **4.1 Authentication Strategy**
```python
# auth/session_manager.py
class SessionManager:
    async def create_session(self, user_identifier: str) -> str:
        """Create authenticated session for MCP client"""
        
    async def validate_session(self, session_token: str) -> bool:
        """Validate MCP session token"""
        
    async def get_user_context(self, session_token: str) -> dict:
        """Get user context from session"""
```

### **4.2 Rate Limiting & Quotas**
```python
# Add rate limiting to prevent abuse
from fastapi_limiter import FastAPILimiter

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Implement per-user rate limiting
    pass
```

---

## 📊 **Configuration & Environment**

### **5.1 Environment Variables**
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcpserver-config
data:
  CART_SERVICE_HOST: "cartservice:7070"
  PRODUCT_SERVICE_HOST: "productcatalogservice:3550"
  DATABASE_HOST: "10.103.0.3"  # Cloud SQL private IP
  MCP_SERVER_PORT: "8080"
  LOG_LEVEL: "INFO"
  ENABLE_METRICS: "true"
```

### **5.2 Secrets Management**
```yaml
# Use existing Cloud SQL secret
env:
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: cloudsql-secret-private
      key: password
```

---

## 🧪 **Testing Strategy**

### **6.1 Unit Tests**
```python
# tests/test_cart_tools.py
import pytest
from tools.cart_tools import CartTools

@pytest.mark.asyncio
async def test_add_to_cart():
    cart_tools = CartTools()
    result = await cart_tools.add_to_cart("user123", "product456", 2)
    assert result.success == True
```

### **6.2 Integration Tests**
```python
# tests/test_integration.py
async def test_full_shopping_flow():
    # Test complete flow: search → add to cart → checkout
    pass
```

---

## 📈 **Monitoring & Observability**

### **7.1 Metrics Collection**
```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram

mcp_requests_total = Counter('mcp_requests_total', 'Total MCP requests')
mcp_request_duration = Histogram('mcp_request_duration_seconds', 'MCP request duration')
```

### **7.2 Logging Strategy**
```python
import structlog

logger = structlog.get_logger()
logger.info("MCP tool called", tool_name="add_to_cart", user_id=user_id)
```

---

## 🎯 **Usage Examples**

### **8.1 AI Assistant Interactions**
```
User: "Add 2 vintage cameras to my cart"
Assistant: [Calls MCP] → search_products("vintage camera") → add_to_cart(user_id, "CAMERA001", 2)
Response: "I've added 2 vintage cameras to your cart for $179.98 total."

User: "What's in my cart?"
Assistant: [Calls MCP] → get_cart_contents(user_id)
Response: "Your cart contains: 2x Vintage Camera ($89.99 each), 1x Travel Backpack ($67.99)"
```

### **8.2 Advanced Workflows**
```
User: "Find me products under $50 for outdoor activities"
Assistant: [Calls MCP] → search_products("outdoor") → filter by price
Response: "I found 5 outdoor products under $50: Ceramic Plant Pot ($15.99), Cotton T-Shirt ($24.99)..."
```

---

## 🚧 **Implementation Timeline**

### **Week 1-2: Infrastructure**
- [ ] Create MCP server microservice structure
- [ ] Set up gRPC clients for existing services
- [ ] Basic FastAPI server with health checks

### **Week 3-4: Core Tools**
- [ ] Implement cart management tools
- [ ] Implement product search/browse tools
- [ ] Add session management and auth

### **Week 5-6: Integration & Testing**
- [ ] Deploy to Kubernetes cluster
- [ ] Integration testing with existing services
- [ ] Performance optimization

### **Week 7-8: Production Ready**
- [ ] Security hardening
- [ ] Monitoring and alerting setup
- [ ] Documentation and training

---

## 💡 **Benefits**

1. **AI-Powered Shopping**: Natural language interaction with the store
2. **Developer Productivity**: Easy integration with AI development tools
3. **Customer Support**: AI assistants can help customers navigate the store
4. **Analytics**: Track AI-driven shopping patterns
5. **Extensibility**: Easy to add new tools and capabilities

This plan provides a comprehensive approach to creating MCP servers that bridge AI assistants with your Online Boutique microservices, enabling powerful AI-driven shopping experiences! 🛍️🤖 