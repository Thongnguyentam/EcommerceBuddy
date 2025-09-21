# Image Assistant Service

A microservice that provides generic image analysis and product visualization capabilities using Google Cloud Vision API and Vertex AI Generative AI.

## Features

### 1. Image Analysis (`/analyze`)
Analyzes images to detect:
- **Objects**: Object detection with bounding boxes and confidence scores
- **Scene Type**: Classification of scene type (indoor, outdoor, portrait, etc.)
- **Styles**: Artistic or photographic style detection
- **Colors**: Dominant color extraction
- **Tags**: General descriptive tags

**Input:**
```json
{
  "image_url": "https://example.com/image.jpg",
  "context": "optional context for analysis"
}
```

**Output:**
```json
{
  "objects": [
    {
      "label": "person",
      "confidence": 0.95,
      "box": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.6}
    }
  ],
  "scene_type": "outdoor",
  "styles": ["modern", "professional"],
  "colors": ["#ff0000", "#00ff00"],
  "tags": ["person", "building", "sky"]
}
```

### 2. Product Visualization (`/visualize`)
Renders product overlays in user photos using AI image generation:

**Input:**
```json
{
  "base_image_url": "https://example.com/room.jpg",
  "product_image_url": "https://example.com/chair.jpg",
  "placement": {
    "position": {"x": 0.5, "y": 0.7},
    "scale": 0.3,
    "rotation": 15.0,
    "occlusion_mask_url": "https://example.com/mask.jpg"
  },
  "prompt": "Place the chair naturally in the living room"
}
```

**Output:**
```json
{
  "render_url": "https://storage.googleapis.com/renders/result.jpg",
  "metadata": {
    "latency_ms": 1500,
    "seed": 12345
  }
}
```

## Architecture

The service provides both **gRPC** and **HTTP REST** interfaces:

- **gRPC Server**: Port 8080 (default) - For high-performance inter-service communication
- **HTTP Server**: Port 8000 (default) - For web client integration
- **Health Checks**: Available on both protocols

## Technology Stack

- **FastAPI**: HTTP REST API framework
- **gRPC**: High-performance RPC framework
- **Google Cloud Vision API**: Object detection and image analysis
- **Vertex AI**: Generative AI for image manipulation
- **Pydantic**: Data validation and serialization
- **AsyncIO**: Asynchronous processing

## Setup

### Prerequisites

1. **Google Cloud Project** with the following APIs enabled:
   - Vision API
   - Vertex AI API
   - Cloud Storage API (for image storage)

2. **Authentication**: Set up Application Default Credentials
   ```bash
   gcloud auth application-default login
   ```

3. **Environment Variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   export GOOGLE_CLOUD_REGION="us-central1"
   export PORT="8080"              # gRPC port
   export HTTP_PORT="8000"         # HTTP port
   export ENABLE_HTTP="true"       # Enable HTTP server
   ```

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate gRPC Code**:
   ```bash
   ./genproto.sh
   ```

3. **Run the Service**:
   ```bash
   python server.py
   ```

### Docker Deployment

1. **Build Image**:
   ```bash
   docker build -t imageassistant-service .
   ```

2. **Run Container**:
   ```bash
   docker run -p 8080:8080 -p 8000:8000 \
     -e GOOGLE_CLOUD_PROJECT=your-project \
     -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json \
     -v /path/to/credentials.json:/path/to/credentials.json \
     imageassistant-service
   ```

## API Usage

### HTTP REST API

```bash
# Health check
curl http://localhost:8000/health

# Analyze image
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/image.jpg"}'

# Visualize product
curl -X POST http://localhost:8000/visualize \
  -H "Content-Type: application/json" \
  -d '{
    "base_image_url": "https://example.com/room.jpg",
    "product_image_url": "https://example.com/chair.jpg"
  }'
```

### gRPC API

Use the generated client code in `genproto/` directory:

```python
import grpc
from genproto import imageassistant_pb2, imageassistant_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:8080')
stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)

# Analyze image
request = imageassistant_pb2.AnalyzeImageRequest(
    image_url="https://example.com/image.jpg"
)
response = stub.AnalyzeImage(request)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | - | GCP Project ID (required) |
| `GOOGLE_CLOUD_REGION` | `us-central1` | GCP Region for Vertex AI |
| `PORT` | `8080` | gRPC server port |
| `HTTP_PORT` | `8000` | HTTP server port |
| `ENABLE_HTTP` | `true` | Enable HTTP server alongside gRPC |

### Service Modes

- **gRPC Only**: Set `ENABLE_HTTP=false`
- **Both Protocols**: Set `ENABLE_HTTP=true` (default)

## Testing

Run tests using pytest:

```bash
# Install test dependencies
source  ./env/bin/activate
pip install pytest pytest-asyncio pytest-grpc

# Run tests
pytest tests/
```

## Performance Considerations

- **Async Processing**: All operations are asynchronous for better throughput
- **Parallel Analysis**: Multiple Vision API calls are made in parallel
- **Image Caching**: Consider implementing image caching for frequently analyzed images
- **Rate Limiting**: Be aware of Google Cloud API quotas and rate limits

## Error Handling

The service provides comprehensive error handling:

- **HTTP**: Standard HTTP status codes with detailed error messages
- **gRPC**: Proper gRPC status codes with error details
- **Logging**: Structured logging for debugging and monitoring

## Security

- **Authentication**: Uses Google Cloud Application Default Credentials
- **HTTPS**: Ensure all image URLs use HTTPS
- **Input Validation**: All inputs are validated using Pydantic models
- **Non-root User**: Docker container runs as non-root user

## Monitoring

- **Health Checks**: Available on both HTTP (`/health`) and gRPC protocols
- **Logging**: Structured logs for monitoring and debugging
- **Metrics**: Consider integrating with Google Cloud Monitoring
