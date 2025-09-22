# 🚀 **EcommerceBuddy – The Ultimate AI-Powered Online Shopping Hub**

<!-- <p align="center">
<img src="/src/frontend/static/icons/Hipster_HeroLogoMaroon.svg" width="300" alt="Online Boutique" />
</p> -->
![Continuous Integration](https://github.com/GoogleCloudPlatform/microservices-demo/workflows/Continuous%20Integration%20-%20Main/Release/badge.svg)

**Online Boutique** is a cloud-first microservices demo application.  The application is a
web-based e-commerce app where users can browse items, add them to the cart, and purchase them.

**🤖 NEW: AI-Powered Shopping Agents** - This application now features an advanced AI agent system powered by **Gemini 2.5 Flash** that provides intelligent shopping assistance through natural language conversations, image analysis, and personalized product recommendations.

Google uses this application to demonstrate how developers can modernize enterprise applications using Google Cloud products, including: [Google Kubernetes Engine (GKE)](https://cloud.google.com/kubernetes-engine), [Cloud Service Mesh (CSM)](https://cloud.google.com/service-mesh), [gRPC](https://grpc.io/), [Cloud Operations](https://cloud.google.com/products/operations), [Spanner](https://cloud.google.com/spanner), [Memorystore](https://cloud.google.com/memorystore), [AlloyDB](https://cloud.google.com/alloydb), **[Gemini](https://ai.google.dev/)**, **[Vertex AI](https://cloud.google.com/vertex-ai)**, **[Cloud SQL](https://cloud.google.com/sql)**, and **[Cloud Storage](https://cloud.google.com/storage)**. This application works on any Kubernetes cluster.

If you’re using this demo, please **★Star** this repository to show your interest!

**Note to Googlers:** Please fill out the form at [go/microservices-demo](http://go/microservices-demo).

## Architecture

**Online Boutique** is composed of **16 microservices** (11 original + 5 AI-powered) written in different
languages that talk to each other over gRPC and HTTP APIs.

[![Architecture of
microservices](/docs/img/architecture-diagram.png)](/docs/img/architecture-diagram.png)

### 🤖 NEW AI Agent System Architecture

The application now includes an **intelligent agent orchestration system** that coordinates multiple specialized AI agents:

![Architecture of microservices](https://drive.google.com/uc?id=1oE618tiLCXiHIso8NOjbdNT4ADwIDrV-)

### Core E-commerce Services

| Service                                              | Language      | Description                                                                                                                       |
| ---------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [frontend](/src/frontend)                           | Go            | Exposes an HTTP server to serve the website. Does not require signup/login and generates session IDs for all users automatically. |
| [cartservice](/src/cartservice)                     | C#            | Stores the items in the user's shopping cart in Redis and retrieves it.                                                           |
| [productcatalogservice](/src/productcatalogservice) | Go            | **🧠 Enhanced with RAG**: Provides semantic search using Vertex AI embeddings and Cloud SQL. Supports natural language product queries. |
| [currencyservice](/src/currencyservice)             | Node.js       | Converts one money amount to another currency. Uses real values fetched from European Central Bank. It's the highest QPS service. |
| [paymentservice](/src/paymentservice)               | Node.js       | Charges the given credit card info (mock) with the given amount and returns a transaction ID.                                     |
| [shippingservice](/src/shippingservice)             | Go            | Gives shipping cost estimates based on the shopping cart. Ships items to the given address (mock)                                 |
| [emailservice](/src/emailservice)                   | Python        | Sends users an order confirmation email (mock).                                                                                   |
| [checkoutservice](/src/checkoutservice)             | Go            | Retrieves user cart, prepares order and orchestrates the payment, shipping and the email notification.                            |
| [recommendationservice](/src/recommendationservice) | Python        | Recommends other products based on what's given in the cart.                                                                      |
| [adservice](/src/adservice)                         | Java          | Provides text ads based on given context words.                                                                                   |
| [loadgenerator](/src/loadgenerator)                 | Python/Locust | Continuously sends requests imitating realistic user shopping flows to the frontend.                                              |

### 🤖 AI-Powered Services & Agents

| Service                                              | Language      | Google Cloud Technologies | Description                                                                                                                       |
| ---------------------------------------------------- | ------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| [**agentservice**](/src/agentservice)               | Python        | **Gemini 2.5 Flash**, Vertex AI | **Orchestrator + Domain Agents**: Coordinates intelligent shopping workflows across specialized AI agents for natural language shopping assistance. |
| [**mcpserver**](/src/mcpserver)                     | Python        | FastAPI, Cloud Run | **Tool Discovery Hub**: Centralized Model Context Protocol server that exposes all microservice operations as discoverable AI tools. |
| [**imageassistantservice**](/src/imageassistantservice) | Python    | **Gemini 2.5 Flash Image**, Vision API, Cloud Storage | **"Nano Banana" Visualizer**: Advanced image analysis and AI-powered product visualization using Gemini 2.5 Flash Image Preview. |
| [**reviewservice**](/src/reviewservice)             | Python        | **Cloud SQL**, AlloyDB | **Review Intelligence**: gRPC service for product reviews with sentiment analysis and review aggregation. |
| [**embeddingservice**](/src/embeddingservice)       | Python        | **Vertex AI Embeddings** | **Semantic Understanding**: Generates text embeddings using Vertex AI's text-embedding-004 model for semantic search. |
| [**embeddingworker**](/src/embeddingworker)         | Python        | **Cloud SQL**, PostgreSQL LISTEN/NOTIFY | **Real-time RAG**: Event-driven worker that automatically generates embeddings when product data changes. |

## 🤖 AI Agent Workflow & Capabilities

### Intelligent Shopping Assistant

The AI agent system provides a **conversational shopping experience** powered by **Gemini 2.5 Flash**:

#### 🧠 **Orchestrator Agent**
- **Natural Language Understanding**: Analyzes user queries to determine intent and required services
- **Workflow Planning**: Creates multi-step plans across different domain agents
- **Tool Discovery**: Dynamically discovers available tools through the MCP server
- **Response Synthesis**: Combines results from multiple agents into coherent responses

#### 🎯 **Specialized Domain Agents**
- **🛍️ Product Agent**: Semantic product search using RAG with Vertex AI embeddings
- **🖼️ Image Agent**: Advanced image analysis and "Nano Banana" product visualization
- **🛒 Cart Agent**: Intelligent cart management and recommendations
- **💰 Currency Agent**: Multi-currency support with real-time conversion
- **⭐ Sentiment Agent**: Review analysis and sentiment-based recommendations

### Key AI Features

#### 🔍 **Semantic Product Search**
```
User: "Find me a cozy reading chair for a small apartment"
→ Product Agent uses RAG to search embeddings in Cloud SQL
→ Returns semantically relevant furniture with style matching
```

#### 🎨 **"Nano Banana" Product Visualization**
```
User: "Show me how this vase would look in my living room [image]"
→ Image Agent analyzes room image with Vision API
→ Gemini 2.5 Flash Image Preview generates photorealistic visualization
→ Result stored in Cloud Storage with signed URL
```

#### 💬 **Multi-turn Conversations**
```
User: "I need furniture for my home office"
→ Agent: Shows desk options
User: "Something more modern"
→ Agent: Refines search using conversation context
User: "Add the white desk to my cart"
→ Agent: Processes cart addition and suggests accessories
```

#### 📊 **Review Intelligence**
```
User: "What do people think about this chair?"
→ Review Service aggregates sentiment from Cloud SQL
→ Sentiment Agent provides summary with key themes
→ Includes rating distribution and highlight quotes
```

### Google Cloud AI Stack Integration

| AI Capability | Google Cloud Service | Implementation |
|---------------|---------------------|----------------|
| **Natural Language** | **Gemini 2.5 Flash** | Agent reasoning, conversation, planning |
| **Image Understanding** | **Vision API + Gemini** | Object detection, scene analysis |
| **Product Visualization** | **Gemini 2.5 Flash Image** | Photorealistic product placement |
| **Semantic Search** | **Vertex AI Embeddings** | RAG with text-embedding-004 model |
| **Vector Storage** | **Cloud SQL + pgvector** | High-performance semantic search |
| **Real-time Processing** | **PostgreSQL LISTEN/NOTIFY** | Event-driven embedding generation |
| **Secure Storage** | **Cloud Storage** | Generated images with signed URLs |

### Service Documentation

For detailed implementation guides:
- **[Agent Service](/src/agentservice)** - Multi-agent orchestration system
- **[MCP Server](/src/mcpserver)** - Tool discovery and coordination hub  
- **[Image Assistant](/src/imageassistantservice/README.md)** - "Nano Banana" visualization engine
- **[Review Service](/src/reviewservice/README.md)** - Intelligent review management
- **[Product Catalog](/src/productcatalogservice/README.md)** - RAG-enhanced product search
- **[Embedding Service](/src/embeddingservice/README.md)** - Vertex AI embedding generation
- **[Embedding Worker](/src/embeddingworker/Readme.md)** - Real-time RAG processing

## Screenshots

| Home Page                                                                                                         | Checkout Screen                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [![Screenshot of store homepage](/docs/img/online-boutique-frontend-1.png)](/docs/img/online-boutique-frontend-1.png) | [![Screenshot of checkout screen](/docs/img/online-boutique-frontend-2.png)](/docs/img/online-boutique-frontend-2.png) |

## Quickstart (GKE)

1. Ensure you have the following requirements:
   - [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project).
   - Shell environment with `gcloud`, `git`, and `kubectl`.

2. Clone the latest major version.

   ```sh
   git clone --depth 1 --branch v0 https://github.com/GoogleCloudPlatform/microservices-demo.git
   cd microservices-demo/
   ```

   The `--depth 1` argument skips downloading git history.

3. Set the Google Cloud project and region and ensure the Google Kubernetes Engine API is enabled.

   ```sh
   export PROJECT_ID=<PROJECT_ID>
   export REGION=us-central1
   gcloud services enable container.googleapis.com \
     --project=${PROJECT_ID}
   ```

   Substitute `<PROJECT_ID>` with the ID of your Google Cloud project.

4. Create a GKE cluster and get the credentials for it.

   ```sh
   gcloud container clusters create-auto online-boutique \
     --project=${PROJECT_ID} --region=${REGION}
   ```

   Creating the cluster may take a few minutes.

5. Deploy Online Boutique to the cluster.

   ```sh
   kubectl apply -f ./release/kubernetes-manifests.yaml
   ```

6. Wait for the pods to be ready.

   ```sh
   kubectl get pods
   ```

   After a few minutes, you should see the Pods in a `Running` state:

   ```
   NAME                                     READY   STATUS    RESTARTS   AGE
   adservice-76bdd69666-ckc5j               1/1     Running   0          2m58s
   cartservice-66d497c6b7-dp5jr             1/1     Running   0          2m59s
   checkoutservice-666c784bd6-4jd22         1/1     Running   0          3m1s
   currencyservice-5d5d496984-4jmd7         1/1     Running   0          2m59s
   emailservice-667457d9d6-75jcq            1/1     Running   0          3m2s
   frontend-6b8d69b9fb-wjqdg                1/1     Running   0          3m1s
   loadgenerator-665b5cd444-gwqdq           1/1     Running   0          3m
   paymentservice-68596d6dd6-bf6bv          1/1     Running   0          3m
   productcatalogservice-557d474574-888kr   1/1     Running   0          3m
   recommendationservice-69c56b74d4-7z8r5   1/1     Running   0          3m1s
   redis-cart-5f59546cdd-5jnqf              1/1     Running   0          2m58s
   shippingservice-6ccc89f8fd-v686r         1/1     Running   0          2m58s
   ```

7. Access the web frontend in a browser using the frontend's external IP.

   ```sh
   kubectl get service frontend-external | awk '{print $4}'
   ```

   Visit `http://EXTERNAL_IP` in a web browser to access your instance of Online Boutique.

8. Congrats! You've deployed the default Online Boutique. To deploy a different variation of Online Boutique (e.g., with Google Cloud Operations tracing, Istio, etc.), see [Deploy Online Boutique variations with Kustomize](#deploy-online-boutique-variations-with-kustomize).

9. Once you are done with it, delete the GKE cluster.

   ```sh
   gcloud container clusters delete online-boutique \
     --project=${PROJECT_ID} --region=${REGION}
   ```

   Deleting the cluster may take a few minutes.

## Additional deployment options

- **Terraform**: [See these instructions](/terraform) to learn how to deploy Online Boutique using [Terraform](https://www.terraform.io/intro).
- **Istio / Cloud Service Mesh**: [See these instructions](/kustomize/components/service-mesh-istio/README.md) to deploy Online Boutique alongside an Istio-backed service mesh.
- **Non-GKE clusters (Minikube, Kind, etc)**: See the [Development guide](/docs/development-guide.md) to learn how you can deploy Online Boutique on non-GKE clusters.
- **🤖 AI Shopping Agents**: Deploy the full AI agent system with Gemini 2.5 Flash, semantic search, and "Nano Banana" product visualization:
  ```bash
  # Deploy with AI agents and Cloud SQL
  cd kustomization
  kubectl apply -k .
  ```
- **🧠 RAG-Enhanced Product Search**: Enable semantic search with Vertex AI embeddings and Cloud SQL vector storage
- **📊 Review Intelligence**: Deploy review service with sentiment analysis and Cloud SQL integration
- **🎨 "Nano Banana" Image Generation**: Advanced product visualization using Gemini 2.5 Flash Image Preview
- **And more**: The [`/kustomize` directory](/kustomize) contains instructions for customizing the deployment of Online Boutique with other variations.

## Documentation

- [Development](/docs/development-guide.md) to learn how to run and develop this app locally.

## Demos featuring Online Boutique

- [Platform Engineering in action: Deploy the Online Boutique sample apps with Score and Humanitec](https://medium.com/p/d99101001e69)
- [The new Kubernetes Gateway API with Istio and Anthos Service Mesh (ASM)](https://medium.com/p/9d64c7009cd)
- [Use Azure Redis Cache with the Online Boutique sample on AKS](https://medium.com/p/981bd98b53f8)
- [Sail Sharp, 8 tips to optimize and secure your .NET containers for Kubernetes](https://medium.com/p/c68ba253844a)
- [Deploy multi-region application with Anthos and Google cloud Spanner](https://medium.com/google-cloud/a2ea3493ed0)
- [Use Google Cloud Memorystore (Redis) with the Online Boutique sample on GKE](https://medium.com/p/82f7879a900d)
- [Use Helm to simplify the deployment of Online Boutique, with a Service Mesh, GitOps, and more!](https://medium.com/p/246119e46d53)
- [How to reduce microservices complexity with Apigee and Anthos Service Mesh](https://cloud.google.com/blog/products/application-modernization/api-management-and-service-mesh-go-together)
- [gRPC health probes with Kubernetes 1.24+](https://medium.com/p/b5bd26253a4c)
- [Use Google Cloud Spanner with the Online Boutique sample](https://medium.com/p/f7248e077339)
- [Seamlessly encrypt traffic from any apps in your Mesh to Memorystore (redis)](https://medium.com/google-cloud/64b71969318d)
- [Strengthen your app's security with Cloud Service Mesh and Anthos Config Management](https://cloud.google.com/service-mesh/docs/strengthen-app-security)
- [From edge to mesh: Exposing service mesh applications through GKE Ingress](https://cloud.google.com/architecture/exposing-service-mesh-apps-through-gke-ingress)
- [Take the first step toward SRE with Cloud Operations Sandbox](https://cloud.google.com/blog/products/operations/on-the-road-to-sre-with-cloud-operations-sandbox)
- [Deploying the Online Boutique sample application on Cloud Service Mesh](https://cloud.google.com/service-mesh/docs/onlineboutique-install-kpt)
- [Anthos Service Mesh Workshop: Lab Guide](https://codelabs.developers.google.com/codelabs/anthos-service-mesh-workshop)
- [KubeCon EU 2019 - Reinventing Networking: A Deep Dive into Istio's Multicluster Gateways - Steve Dake, Independent](https://youtu.be/-t2BfT59zJA?t=982)
- Google Cloud Next'18 SF
  - [Day 1 Keynote](https://youtu.be/vJ9OaAqfxo4?t=2416) showing GKE On-Prem
  - [Day 3 Keynote](https://youtu.be/JQPOPV_VH5w?t=815) showing Stackdriver
    APM (Tracing, Code Search, Profiler, Google Cloud Build)
  - [Introduction to Service Management with Istio](https://www.youtube.com/watch?v=wCJrdKdD6UM&feature=youtu.be&t=586)
- [Google Cloud Next'18 London – Keynote](https://youtu.be/nIq2pkNcfEI?t=3071)
  showing Stackdriver Incident Response Management
- [Microservices demo showcasing Go Micro](https://github.com/go-micro/demo)
