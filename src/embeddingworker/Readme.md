# Embedding Worker Service

A PostgreSQL LISTEN/NOTIFY-based worker service that automatically generates semantic embeddings for product data using Google Vertex AI.

## Architecture Overview

This service implements an event-driven architecture where database changes trigger real-time embedding generation through PostgreSQL's LISTEN/NOTIFY mechanism.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   Application   │    │   PostgreSQL     │    │ Embedding       │    │ Vertex AI        │
│   (Insert/      │───▶│   Database       │───▶│ Worker          │───▶│ Embedding        │
│    Update)      │    │                  │    │ Service         │    │ Service          │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └──────────────────┘
                              │                         │
                              │ pg_notify              │ HTTP POST
                              ▼                         ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ embedding_jobs   │    │ /embed          │
                       │ channel          │    │ endpoint        │
                       └──────────────────┘    └─────────────────┘
                              │                         │
                              │ LISTEN                  │ Real-time
                              ▼                         │ embeddings
                       ┌──────────────────┐            │
                       │ Worker Process   │◀───────────┘
                       │ (Python)         │
                       └──────────────────┘
                              │
                              │ UPDATE with embeddings
                              ▼
                       ┌──────────────────┐
                       │ products table   │
                       │ (with vectors)   │
                       └──────────────────┘
```

## How It Works

### 1. Database Setup

#### PostgreSQL Notification Function
```sql
CREATE OR REPLACE FUNCTION notify_for_embedding() RETURNS trigger AS $$
DECLARE
  payload json;
BEGIN
  -- Build payload with all required data
  payload := json_build_object(
    'id', NEW.id,
    'name', COALESCE(NEW.name, ''),
    'description', COALESCE(NEW.description, ''),
    'categories', COALESCE(NEW.categories, ''),
    'target_tags', COALESCE(array_to_string(NEW.target_tags, ' '), ''),
    'use_context', COALESCE(array_to_string(NEW.use_context, ' '), '')
  );
  
  -- Notify the embedding worker
  PERFORM pg_notify('embedding_jobs', payload::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

This function:
- Triggers on every `INSERT` or `UPDATE` to the `products` table
- Extracts all relevant text fields from the product record
- Packages them into a JSON payload
- Sends a real-time notification to the `embedding_jobs` channel

#### Database Trigger
```sql
CREATE TRIGGER embedding_notification_trigger
AFTER INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION notify_for_embedding();
```

The trigger:
- Fires **after** the database operation completes
- Ensures data consistency before processing
- Works for both new products and updates to existing ones

### 2. Worker Service Architecture

The Python worker service (`embedding_worker.py`) implements:

#### LISTEN/NOTIFY Pattern
```python
# Listen for notifications
cursor.execute("LISTEN embedding_jobs;")

while True:
    # Wait for notifications with timeout
    if select.select([conn], [], [], 5) == ([], [], []):
        continue
    
    conn.poll()
    while conn.notifies:
        notify = conn.notifies.pop(0)
        payload = json.loads(notify.payload)
        process_embedding_job(payload)
```

#### Embedding Generation Process
For each notification, the worker:

1. **Receives** the product data via PostgreSQL notification
2. **Prepares** multiple text variants for embedding:
   - `description`: Product description text
   - `categories`: Product category string
   - `combined`: Name + description + categories
   - `target_tags`: Space-separated target tags
   - `use_context`: Space-separated use context tags

3. **Calls** the Vertex AI embedding service for each text variant
4. **Converts** embeddings to PostgreSQL vector format
5. **Updates** the database with all generated embeddings

#### Error Handling & Resilience
- **Service Health Checks**: Validates embedding service availability on startup
- **Individual Job Failure**: Failed embeddings don't block other products
- **Retry Logic**: Automatic reconnection for database/service failures
- **Graceful Degradation**: Continues processing even if some embeddings fail

### 3. Database Schema

The `products` table includes vector columns for semantic search:

```sql
CREATE TABLE products (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    categories TEXT,
    target_tags TEXT[],
    use_context TEXT[],
    
    -- Vector embeddings (768 dimensions for Vertex AI text-embedding-004)
    description_embedding VECTOR(768),
    category_embedding VECTOR(768),
    combined_embedding VECTOR(768),
    target_tags_embedding VECTOR(768),
    use_context_embedding VECTOR(768)
);
```

### 4. Semantic Search Implementation

The system supports hybrid search combining multiple embedding types:

```sql
SELECT 
    p.id, p.name, p.description,
    (
        COALESCE(p.combined_embedding <=> query_embedding, 1.0) * 0.6 +
        COALESCE(p.target_tags_embedding <=> query_embedding, 1.0) * 0.2 +
        COALESCE(p.use_context_embedding <=> query_embedding, 1.0) * 0.2
    ) as similarity_score
FROM products p
WHERE p.combined_embedding IS NOT NULL
ORDER BY similarity_score ASC
LIMIT 10;
```

**Weighting Strategy:**
- **60%** Combined embedding (name + description + categories)
- **20%** Target tags embedding (specific product attributes)
- **20%** Use context embedding (usage scenarios)

## Deployment Architecture

### Kubernetes Components

1. **EmbeddingWorker Deployment**
   - Python service with PostgreSQL and HTTP client dependencies
   - Workload Identity for secure GCP service access
   - Health checks and resource limits

2. **Service Dependencies**
   - **PostgreSQL Database**: Cloud SQL with pgvector extension
   - **Embedding Service**: Vertex AI embedding service (HTTP)
   - **IAM & Security**: Workload Identity, service accounts

### Environment Configuration

```yaml
env:
- name: DB_HOST
  value: "10.103.0.3"  # Cloud SQL private IP
- name: DB_USER
  value: "postgres"
- name: DB_PASSWORD
  value: "Admin123"
- name: DB_NAME
  value: "products"
- name: EMBEDDING_SERVICE_URL
  value: "http://embeddingservice:8081"
```

## Advantages of This Approach

### 1. **Real-time Processing**
- Embeddings generated immediately when products are added/updated
- No batch processing delays
- Always up-to-date semantic search results

### 2. **Scalability**
- Worker can be horizontally scaled (multiple pods)
- PostgreSQL LISTEN/NOTIFY handles load balancing automatically
- Decoupled architecture allows independent scaling

### 3. **Reliability**
- Database transactions ensure consistency
- Failed embedding jobs don't affect database operations
- Worker can restart and resume processing seamlessly

### 4. **Flexibility**
- Easy to add new embedding types
- Configurable weighting strategies
- Support for different embedding models

### 5. **Cost Efficiency**
- Only generates embeddings when needed (on data changes)
- No periodic batch processing overhead
- Efficient resource utilization

## Monitoring & Observability

The worker service provides:

- **Structured Logging**: JSON-formatted logs with timestamps
- **Health Metrics**: Success/failure counts and processing statistics
- **Error Tracking**: Detailed error messages for debugging
- **Performance Metrics**: Processing times and throughput

Example log output:
```
2025-09-20 15:24:23,208 - INFO - 🔄 Processing embedding job for product: SOFA001
2025-09-20 15:24:23,275 - INFO -   ✅ Generated description embedding (768 dimensions)
2025-09-20 15:24:23,342 - INFO -   ✅ Generated categories embedding (768 dimensions)
2025-09-20 15:24:23,408 - INFO -   ✅ Updated embeddings for product SOFA001
```

## Troubleshooting

### Common Issues

1. **Worker Not Processing Jobs**
   - Check database connectivity
   - Verify LISTEN command was executed
   - Confirm embedding service is accessible

2. **Embedding Generation Failures**
   - Validate Vertex AI service account permissions
   - Check embedding service health endpoint
   - Review worker logs for specific error messages

3. **Database Connection Issues**
   - Verify Cloud SQL private IP connectivity
   - Check Workload Identity configuration
   - Confirm database credentials and permissions

### Debugging Commands

```bash
# Check worker logs
kubectl logs -l app=embeddingworker --tail=50

# Test database connectivity
kubectl exec -it deployment/embeddingworker -- python -c "import psycopg2; print('OK')"

# Verify embedding service
kubectl port-forward svc/embeddingservice 8081:8081
curl localhost:8081/health

# Check database notifications
# (From database connection)
LISTEN embedding_jobs;
-- Insert test product and wait for notification
```

## Performance Considerations

- **Batch Size**: Worker processes one notification at a time for reliability
- **Rate Limiting**: Built-in delays prevent overwhelming the embedding service
- **Memory Usage**: Optimized for processing individual products
- **Network Efficiency**: Reuses database connections and HTTP clients

## Security

- **Workload Identity**: No service account keys stored in containers
- **Network Isolation**: Private Cloud SQL and internal Kubernetes networking
- **Least Privilege**: Minimal IAM permissions for database and embedding access
- **Secret Management**: Database passwords via Kubernetes secrets or Secret Manager
