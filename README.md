# Travel Multi-Agent Workshop with Fabric Analytics

## Overview

This workshop walks through how to build a multi-agent travel assistant system using Python, LangGraph, Azure OpenAI, and Azure Cosmos DB. You'll create specialized AI agents that work together to help users plan travel arrangements, learn about agent memory orchestration, and then analyze how those agents learn and make decisions using Microsoft Fabric and Power BI.

### What You'll Build

By the end of this workshop, you'll have created a complete travel planning application featuring:

- **Multiple specialized agents**: Hotel booking agent, dining recommendations agent, activity planning agent, and more
- **Intelligent orchestration**: A coordinator agent that manages interactions between specialized agents
- **Memory system**: Persistent memory storage using Azure Cosmos DB to remember user preferences and past interactions — including declarative facts, behavioral patterns, and trip-specific context
- **Modern web interface**: An Angular frontend that provides an intuitive chat interface
- **API layer**: A FastAPI backend that orchestrates all agent interactions
- **Analytics pipeline**: Microsoft Fabric integration with Cosmos DB mirroring, Spark notebooks, and Power BI reports that visualize how agents learn about users, handle preference conflicts, and personalize trip recommendations over time

### Learning Objectives

- Understand multi-agent architecture patterns and design principles
- Learn to build agents using LangGraph framework with Azure OpenAI
- Implement agent specialization and tool integration
- Add intelligent memory systems to enhance agent interactions
- Practice observability and experimentation techniques
- Deploy and manage AI applications on Azure
- Analyze multi-agent memory patterns, trip planning behavior, and user preference evolution using Microsoft Fabric

## Getting Started

This repository contains three main directories:

### 📚 **01_exercises** - The Workshop
Navigate to this folder to follow along with the step-by-step workshop modules. Start here if you want to build the solution from scratch and learn each concept progressively.

### ✅ **02_completed** - The complete solution
Navigate to this folder to access the fully implemented solution. Use this if you want to see the end result or deploy the complete application. This is the only folder that supports Azure deployment — the exercises folder is for local development only.

### 📊 **analytics** - Fabric Analytics
Navigate to this folder for the Microsoft Fabric analytics pipeline: data generation, Cosmos DB mirroring, Spark notebooks, and Power BI reporting. See the [Analytics README](analytics/README.md) for full details.

## Deployment to Azure (Complete Solution Only)

The `02_completed` folder supports full deployment to Azure Container Apps. This provisions all infrastructure and deploys three containerized services:

| Service | Type | Description |
|---------|------|-------------|
| **Frontend** | External Container App | Angular web UI served via nginx (public-facing) |
| **API** | Internal Container App | FastAPI multi-agent backend |
| **MCP Server** | Internal Container App | MCP tool server for agent tools |

These deploy on top of the shared Azure resources (Cosmos DB, Azure OpenAI, Managed Identity) that are also provisioned by the deployment.

### Prerequisites

Ensure you have the following installed:
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js and npm](https://nodejs.org/en/download/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (required for building container images)

### Deploy

```bash
git clone -b analytics https://github.com/AzureCosmosDB/travel-multi-agent-workshop.git
cd travel-multi-agent-workshop/02_completed
azd auth login
azd up
```

This command will:
1. Provision Azure resources (Cosmos DB, Azure OpenAI, Container Registry, Container Apps Environment, Log Analytics)
2. Build Docker images for all three services
3. Push images to Azure Container Registry
4. Deploy the containers and seed the Cosmos DB database
5. Restart the API container to establish a fresh MCP session

The deployment takes several minutes. When complete, `azd` prints the service endpoints. The **frontend endpoint** is your public URL — open it in a browser to start using the application.

> **Subsequent deployments:** Running `azd up` again will rebuild and redeploy all services. The `postdeploy` hook automatically restarts the API container so the MCP session is always fresh.

### Access the Deployed Application

After deployment, the frontend URL is printed in the terminal output and also stored in your azd environment:

```bash
azd env get-value FRONTEND_URI
```

Open this URL in your browser. See the [User Guide](02_completed/USER_GUIDE.md) for a walkthrough of the application's features, how to interact with the agents, and how the memory system works.

## Analytics: Analyzing Multi-Agent Memory & Behavior

Once the application is deployed and you've interacted with it (or generated data), the next phase of the workshop focuses on analyzing how the agents learn, remember, and make decisions.

The **[analytics/](analytics/)** folder contains everything you need to build a complete analytics pipeline on top of the travel assistant's operational data:

1. **Generate data** — Simulate 12 diverse user personas having realistic multi-turn conversations with the travel assistant, creating memories, trips, and preference conflicts in Cosmos DB.
2. **Mirror to Fabric** — Set up Cosmos DB mirroring to continuously replicate operational data into Microsoft Fabric as Delta tables — no ETL pipelines required.
3. **Transform with Spark** — Run a Fabric notebook that flattens nested JSON structures and produces 10 analytical tables (silver and gold layers) in your Lakehouse.
4. **Visualize with Power BI** — Build a 5-page report that tells the story of how your agents learn about users, handle changing preferences, plan personalized trips, and recommend destinations.

Head to the **[Analytics README](analytics/README.md)** for the full step-by-step guide covering data generation, Fabric mirroring setup, Spark notebook configuration, and Power BI report creation.

## Local Development

If you prefer to run the services locally instead of using the deployed Container Apps, you can do so after running `azd up` (which provisions the Azure resources and creates `.env` files with the required endpoints).

### Terminal 1 - Start the MCP server:

Open a new terminal, navigate to the `02_completed` directory, then run:

**Linux/macOS:**
```bash
source venv/bin/activate
cd mcp_server
PYTHONPATH=../python python mcp_http_server.py
```

**Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
cd mcp_server
$env:PYTHONPATH="..\python"
python mcp_http_server.py
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
set PYTHONPATH=../python && python mcp_http_server.py
```

### Terminal 2 - Start the Travel API:

Open a new terminal, navigate to the `02_completed` directory, then run:

**Linux/macOS:**
```bash
source venv/bin/activate
cd python
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
cd python
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3 - Start the Frontend:

Open a new terminal, navigate to the `02_completed\frontend` folder, then run:

**All platforms:**
```bash
npm install
npm start
```

Access the applications:

- Travel API: [http://localhost:8000/docs](http://localhost:8000/docs)
- MCP Server: [http://localhost:8080/docs](http://localhost:8080/docs)
- Frontend: [http://localhost:4200](http://localhost:4200/)

## Next Steps

- **[User Guide](02_completed/USER_GUIDE.md)** — Learn how to use the application: navigating the frontend, talking to agents, how memory and personalization work, supported destinations, and tips for best results.
