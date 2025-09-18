# Review Service

A gRPC microservice for managing product reviews in the Online Boutique application. This service provides high-performance, type-safe access to product review data for other microservices.

## Architecture

This service follows the microservices pattern used throughout the Online Boutique application:
- **gRPC API**: High-performance service-to-service communication
- **Cloud SQL Integration**: Persistent storage using Google Cloud SQL/AlloyDB
- **Kubernetes-native**: Health checks, security contexts, and Cloud SQL proxy support
- **Python + AsyncIO**: Async/await for high concurrency

## gRPC Service Definition

The service implements the `ReviewService` with the following methods:

### Core Methods
- `GetProductReviews(GetProductReviewsRequest) -> GetProductReviewsResponse`
  - Retrieve paginated reviews for a specific product
  - Used by ProductCatalog service to show reviews on product pages
  
- `GetProductReviewSummary(GetProductReviewSummaryRequest) -> ProductReviewSummary`
  - Get aggregate statistics: average rating, total count, rating distribution
  - Used by ProductCatalog service for quick product overview

### System Methods  
- `Check(HealthCheckRequest) -> HealthCheckResponse`
  - gRPC health check for Kubernetes readiness/liveness probes

## Protocol Buffers

### Core Messages
```protobuf
message Review {
  int32 id = 1;
  string user_id = 2;
  string product_id = 3;
  int32 rating = 4;           // 1-5 rating
  string review_text = 5;     // Optional review text
  int64 created_at = 6;       // Unix timestamp
  int64 updated_at = 7;       // Unix timestamp
}

message ProductReviewSummary {
  string product_id = 1;
  int32 total_reviews = 2;
  float average_rating = 3;
  map<string, int32> rating_distribution = 4;  // "1" -> count, "2" -> count, etc.
}
```

### Request/Response Messages
```protobuf
message GetProductReviewsRequest {
  string product_id = 1;
  int32 limit = 2;     // Default: 50, Max: 100
  int32 offset = 3;    // For pagination
}

message GetProductReviewsResponse {
  repeated Review reviews = 1;
}

message GetProductReviewSummaryRequest {
  string product_id = 1;
}
```

## Database Schema

```sql
CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_product_review UNIQUE(user_id, product_id)
);

-- Indexes for performance
CREATE INDEX idx_product_reviews_product_id ON product_reviews(product_id);
CREATE INDEX idx_product_reviews_user_id ON product_reviews(user_id);
CREATE INDEX idx_product_reviews_rating ON product_reviews(rating);
```

## Environment Variables

### Required (Cloud SQL)
- `CLOUDSQL_HOST` - Cloud SQL instance private IP
- `ALLOYDB_DATABASE_NAME` - Database name (default: "reviews")
- `ALLOYDB_SECRET_NAME` - Secret Manager secret name for DB password
- `PROJECT_ID` - Google Cloud project ID

### Optional
- `PORT` - Server port (default: 8080)

## Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Generate gRPC code
./genproto.sh

# Run tests
pytest tests/ -v

# Start server (without Cloud SQL)
python server.py
```

### Testing with gRPC Client
```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Test with client
python client_test.py
```

## Deployment

### Kubernetes
The service is deployed as part of the Online Boutique application:

```yaml
# Base deployment
kubectl apply -k kustomize/base/

# With Cloud SQL integration  
kubectl apply -k kustomize/components/cloudsql/
```

### Docker
```bash
# Build image
docker build -t reviewservice .

# Run locally (without Cloud SQL)
docker run -p 8080:8080 reviewservice
```

## Integration with Other Services

### ProductCatalog Service (Go)
The ProductCatalog service should call this service to enrich product data:

```go
// Example Go client code
conn, _ := grpc.Dial("reviewservice:8080", grpc.WithInsecure())
client := review.NewReviewServiceClient(conn)

summary, _ := client.GetProductReviewSummary(ctx, &review.GetProductReviewSummaryRequest{
    ProductId: "product123",
})

fmt.Printf("Average rating: %.1f (%d reviews)", 
    summary.AverageRating, summary.TotalReviews)
```

### Frontend (Web)
For user-facing review functionality, consider adding a REST API layer or using gRPC-Web.

## Performance Considerations

- **Connection Pooling**: SQLAlchemy async engine with connection pooling
- **Pagination**: All list operations support limit/offset pagination
- **Indexing**: Database indexes on frequently queried columns
- **Async/Await**: Non-blocking I/O for high concurrency
- **Resource Limits**: Kubernetes resource requests/limits configured

## Security

- **Non-root Container**: Runs as user ID 1000
- **Read-only Filesystem**: Container filesystem is read-only
- **No Privilege Escalation**: Security contexts prevent privilege escalation
- **Secret Management**: Database credentials stored in Google Secret Manager 