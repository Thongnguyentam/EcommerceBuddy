# Image Assistant Service

A microservice that provides advanced image analysis and AI-powered product visualization using Google Cloud Vision API, Gemini 2.5 Flash, and Vertex AI.

## Features

### 1. 🔍 Intelligent Image Analysis (`AnalyzeImage`)
Advanced image analysis combining Google Cloud Vision API with Gemini-powered style intelligence:

- **Object Detection**: Precise object detection with bounding boxes and confidence scores
- **Scene Classification**: AI-powered scene type detection (indoor, outdoor, portrait, product, etc.)
- **Style Analysis**: Gemini-based artistic and photographic style detection
- **Color Extraction**: Dominant color analysis with hex values
- **Smart Tagging**: Context-aware descriptive tags

**gRPC Request:**
```protobuf
message AnalyzeImageRequest {
  string image_url = 1;
  string context = 2;  // Optional context for better analysis
}
```

**gRPC Response:**
```protobuf
message AnalyzeImageResponse {
  repeated DetectedObject objects = 1;
  string scene_type = 2;
  repeated string styles = 3;
  repeated string colors = 4;
  repeated string tags = 5;
  bool success = 6;
  string message = 7;
}
```

### 2. 🎨 AI Product Visualization (`VisualizeProduct`) - **Nano Banana**
Revolutionary product visualization using **Gemini 2.5 Flash Image Preview** for photorealistic product placement:

**Key Features:**
- **Intelligent Scene Analysis**: AI analyzes both base scene and product for optimal placement
- **Realistic Integration**: Preserves exact product details while seamlessly blending with scene lighting
- **Automatic Placement**: Smart positioning based on scene surfaces, perspective, and composition
- **Photorealistic Results**: Natural shadows, reflections, and lighting adaptation

**gRPC Request:**
```protobuf
message VisualizeProductRequest {
  string base_image_url = 1;     // Scene/room image URL
  string product_image_url = 2;  // Product image URL
  string prompt = 3;             // Placement description
}
```

**gRPC Response:**
```protobuf
message VisualizeProductResponse {
  string render_url = 1;         // Generated image URL
  RenderMetadata metadata = 2;   // Processing metadata
  bool success = 3;
  string message = 4;
}
```

**Example Usage:**
```python
# Place decorative vase on table
request = VisualizeProductRequest(
    base_image_url="https://example.com/living-room.jpg",
    product_image_url="https://example.com/vase.jpg",
    prompt="Place this decorative vase on the coffee table"
)
```

## 🏗️ Architecture

### Service Architecture
- **gRPC Server**: Port 8080 - High-performance inter-service communication
- **Async Processing**: Full asynchronous architecture for optimal throughput
- **Multi-AI Integration**: Combines Vision API, Gemini 2.5 Flash, and intelligent analysis

### AI Pipeline
```
Image Input → Vision API Analysis → Gemini Style Analysis → Results
Product Visualization: Base + Product → Scene Analysis → Gemini 2.5 Flash Image → Photorealistic Output
```

## 🚀 Technology Stack

### Core Framework
- **gRPC**: High-performance RPC communication
- **AsyncIO**: Asynchronous processing pipeline
- **Pydantic**: Data validation and serialization

### AI & ML Services
- **Google Cloud Vision API**: Object detection and image properties
- **Gemini 2.5 Flash**: Intelligent style and scene analysis
- **Gemini 2.5 Flash Image Preview**: Advanced image generation for product visualization
- **Vertex AI**: AI platform integration

### Infrastructure
- **Google Cloud Storage**: Image storage and serving with signed URLs
- **Workload Identity**: Secure GCP authentication in Kubernetes
- **Docker**: Containerized deployment

## 📋 Prerequisites

### Google Cloud Setup
1. **Google Cloud Project** with APIs enabled:
   ```bash
   gcloud services enable vision.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

2. **Service Account**: Create with required permissions:
   ```bash
   gcloud iam service-accounts create imageassistant-sa \
     --display-name="Image Assistant Service Account"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:imageassistant-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:imageassistant-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   ```

3. **GCS Bucket**: For storing generated visualizations:
   ```bash
   gsutil mb gs://PROJECT_ID-image-renders
   ```

## 🛠️ Local Development

### Setup
1. **Install Dependencies**:
   ```bash
   cd src/imageassistantservice
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

2. **Generate gRPC Code**:
   ```bash
   ./genproto.sh
   ```

3. **Environment Configuration**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Run the Service**:
   ```bash
   python server.py
   ```

### Testing
```bash
# Test image analysis
python test_grpc_visualizer.py

# Test Gemini-based product visualization
python test_gemini_visualizer.py
```

## 🚢 Deployment

### Docker Build
```bash
# Build image
docker build -t gcr.io/PROJECT_ID/imageassistantservice:latest .

# Push to registry
docker push gcr.io/PROJECT_ID/imageassistantservice:latest
```

### Kubernetes Deployment
Deploy to GKE using the provided manifests:

```bash
kubectl apply -f kubernetes-manifests/imageassistantservice.yaml
```

The service uses **Workload Identity** for secure GCP authentication without managing service account keys.

## 📊 Performance & Capabilities

### Image Analysis Performance
- **Parallel Processing**: Vision API calls executed concurrently
- **Response Time**: ~1-3 seconds for comprehensive analysis
- **Accuracy**: Enhanced by Gemini-powered style intelligence

### Product Visualization Performance
- **Processing Time**: ~25-30 seconds for photorealistic generation
- **Quality**: High-resolution output with natural lighting and shadows
- **Accuracy**: Preserves exact product details while ensuring realistic integration

### Scalability
- **Async Architecture**: Handles multiple concurrent requests
- **Kubernetes Ready**: Auto-scaling with resource limits
- **GCS Integration**: Efficient image storage and delivery

## 🔧 Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | - | GCP Project ID (required) |
| `GOOGLE_CLOUD_REGION` | `us-central1` | GCP Region for Vertex AI |
| `GCS_RENDERS_BUCKET` | - | GCS bucket for generated images |
| `PORT` | `8080` | gRPC server port |

### Service Configuration
- **Workload Identity**: Automatic GCP authentication in Kubernetes
- **Resource Limits**: Configured for optimal AI workload performance
- **Health Checks**: gRPC health check implementation

## 🧪 API Examples

### Image Analysis
```python
import grpc
from genproto import imageassistant_pb2, imageassistant_pb2_grpc

# Create gRPC client
channel = grpc.insecure_channel('localhost:8080')
stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)

# Analyze image
request = imageassistant_pb2.AnalyzeImageRequest(
    image_url="https://example.com/room.jpg",
    context="Interior design analysis"
)
response = stub.AnalyzeImage(request)

print(f"Scene: {response.scene_type}")
print(f"Styles: {response.styles}")
print(f"Objects: {[obj.label for obj in response.objects]}")
```

### Product Visualization
```python
# Visualize product placement
request = imageassistant_pb2.VisualizeProductRequest(
    base_image_url="https://example.com/living-room.jpg",
    product_image_url="https://example.com/artwork.jpg",
    prompt="Place this artwork naturally on the wall"
)
response = stub.VisualizeProduct(request)

print(f"Generated image: {response.render_url}")
print(f"Processing time: {response.metadata.latency_ms}ms")
```

## 🔒 Security & Best Practices

### Authentication
- **Workload Identity**: Secure, keyless authentication in Kubernetes
- **Service Account Permissions**: Principle of least privilege
- **HTTPS Only**: All external image URLs must use HTTPS

### Input Validation
- **Pydantic Models**: Comprehensive input validation
- **URL Validation**: Secure image URL handling
- **Error Handling**: Graceful error responses with proper gRPC status codes

### Container Security
- **Non-root User**: Container runs as non-privileged user
- **Minimal Base Image**: Alpine Linux for reduced attack surface
- **Resource Limits**: Configured CPU and memory constraints

## 📈 Monitoring & Observability

### Health Checks
- **gRPC Health Check**: Standard gRPC health checking protocol
- **Kubernetes Probes**: Readiness and liveness probes configured

### Logging
- **Structured Logging**: JSON-formatted logs for monitoring
- **Request Tracing**: Comprehensive request/response logging
- **Error Tracking**: Detailed error logging with context

### Metrics
- **Processing Time**: Latency metrics for both analysis and visualization
- **Success Rates**: Request success/failure tracking
- **Resource Usage**: CPU/memory utilization monitoring

## 🚀 Advanced Features

### Intelligent Scene Analysis
The service uses Gemini 2.5 Flash to analyze scenes and products for optimal placement:

1. **Lighting Analysis**: Detects and matches lighting conditions
2. **Surface Detection**: Identifies available placement surfaces
3. **Perspective Matching**: Ensures proper depth and spatial relationships
4. **Style Consistency**: Maintains scene aesthetic and mood

### Photorealistic Integration
Gemini 2.5 Flash Image Preview provides:

- **Exact Product Preservation**: Maintains all original product details
- **Natural Lighting**: Adapts to scene lighting conditions
- **Realistic Shadows**: Generates appropriate contact shadows
- **Seamless Blending**: Natural edge integration without artifacts

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Set up local development environment
3. Run tests: `pytest tests/`
4. Submit pull request

### Code Standards
- **Type Hints**: All functions must include type annotations
- **Async/Await**: Use async patterns for all I/O operations
- **Error Handling**: Comprehensive exception handling
- **Documentation**: Docstrings for all public methods
