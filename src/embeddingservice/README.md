# Vertex AI Embedding Service

A microservice that provides text embeddings using Google Vertex AI's text embedding models.

## Features

- REST API for generating embeddings
- Batch embedding support
- Product-specific embedding endpoint
- Health checks and monitoring
- Fallback handling for API failures
- Kubernetes-ready with proper authentication

## API Endpoints

### Health Check
```
GET /health
```
Returns service status and configuration.

### Single Embedding
```
POST /embed
Content-Type: application/json

{
  "text": "Your text to embed"
}
```

### Batch Embeddings
```
POST /embed/batch
Content-Type: application/json

{
  "texts": ["Text 1", "Text 2", "Text 3"]
}
```

### Product Embeddings
```
POST /embed/product
Content-Type: application/json

{
  "name": "Product Name",
  "description": "Product description",
  "categories": "category1,category2",
  "target_tags": ["tag1", "tag2"],
  "use_context": ["context1", "context2"]
}
```

## Authentication

### For Local Development
1. Create a service account in Google Cloud Console
2. Grant the following roles:
   - `roles/aiplatform.user`
   - `roles/ml.developer`
3. Download the service account key JSON file
4. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/key.json
   ```

### For Kubernetes Deployment
The service uses Workload Identity. Ensure your Kubernetes service account has the necessary permissions.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ID` | `gke-hack-471804` | Google Cloud Project ID |
| `REGION` | `us-central1` | Vertex AI region |
| `EMBEDDING_MODEL` | `text-embedding-004` | Vertex AI embedding model |
| `PORT` | `8081` | Service port |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to service account key (local dev) |

## Testing

### Run Unit Tests
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Run Integration Tests (requires credentials)
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
export RUN_INTEGRATION_TESTS=true
python -m pytest test_embedding_service.py::TestEmbeddingServiceIntegration -v
```

## Building and Deployment

### Build Docker Image
```bash
docker build -t embeddingservice:latest .
```

### Deploy to Kubernetes
```bash
kubectl apply -f ../kubernetes-manifests/embeddingservice.yaml
```

### Test Deployment
```bash
kubectl port-forward svc/embeddingservice 8081:8081
curl http://localhost:8081/health
```

## Usage in Product Catalog Service

The Go product catalog service calls this service for embedding generation:

```go
embeddingServiceURL := "http://embeddingservice:8081"
payload := map[string]string{"text": query}
// Make HTTP POST to /embed endpoint
```

## Error Handling

- Returns zero vectors `[0.0] * 768` for empty/invalid input
- Graceful fallback on API failures
- Comprehensive logging for debugging
- Health check endpoint for monitoring

## Performance

- Single embedding: ~50-200ms
- Batch embeddings: More efficient for multiple texts
- Memory usage: ~512MB-1GB depending on load
- CPU usage: Low when idle, spikes during embedding generation

## Troubleshooting

### Authentication Errors
```
ERROR: Failed to initialize Vertex AI model: 403 Forbidden
```
**Solution**: Check service account permissions and GOOGLE_APPLICATION_CREDENTIALS

### Model Loading Errors
```
ERROR: Failed to initialize Vertex AI model: Model not found
```
**Solution**: Verify PROJECT_ID, REGION, and EMBEDDING_MODEL are correct

### Connection Errors
```
ERROR: Failed to call embedding service: connection refused
```
**Solution**: Check if service is running and accessible at the expected URL 