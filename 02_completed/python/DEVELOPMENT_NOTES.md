# Travel Assistant API - Development Notes

**Project**: Multi-Agent Travel Planning System  
**Stack**: FastAPI, LangGraph, Azure Cosmos DB, Azure OpenAI  
**Created**: October 2025  
**Last Updated**: October 16, 2025

---

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Environment Setup](#environment-setup)
3. [Key Components](#key-components)
4. [Bugs Fixed & Solutions](#bugs-fixed--solutions)
5. [Configuration Reference](#configuration-reference)
6. [API Endpoints](#api-endpoints)
7. [Agent System](#agent-system)
8. [Database Schema](#database-schema)
9. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
10. [Development Workflow](#development-workflow)
11. [Testing Guide](#testing-guide)
12. [Deployment Notes](#deployment-notes)

---

## System Architecture

### High-Level Overview
```
┌─────────────────┐
│   User Request  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│          FastAPI Server (Port 8000)                 │
│  - REST API with 40+ endpoints                      │
│  - Swagger UI: http://localhost:8000/docs           │
│  - Thread management, chat completion               │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│           LangGraph Multi-Agent System              │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Orchestrator │─▶│ Hotel Agent  │                │
│  └──────────────┘  └──────────────┘                │
│         │          ┌──────────────┐                 │
│         ├─────────▶│Dining Agent  │                │
│         │          └──────────────┘                 │
│         │          ┌──────────────┐                 │
│         ├─────────▶│Activity Agent│                │
│         │          └──────────────┘                 │
│         │          ┌──────────────────┐             │
│         ├─────────▶│Itinerary Generator│           │
│         │          └──────────────────┘             │
│         │          ┌──────────────┐                 │
│         └─────────▶│ Summarizer   │                │
│                    └──────────────┘                 │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│        MCP HTTP Server (Port 8080)                  │
│  - discover_places (vector search)                  │
│  - store_user_memory                                │
│  - recall_memories                                  │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│           Azure Cosmos DB                           │
│  - places: Hotels, restaurants, attractions         │
│  - threads: Conversation threads                    │
│  - messages: Chat history                           │
│  - trips: Itineraries                               │
│  - memories: User preferences                       │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│           Azure OpenAI                              │
│  - GPT-4o for agent reasoning                       │
│  - text-embedding-3-large (1024 dims)               │
│  - API Version: 2024-12-01-preview                  │
└─────────────────────────────────────────────────────┘
```

### Data Flow
1. **User sends message** → FastAPI `/completion` endpoint
2. **API creates/loads thread** → Cosmos DB threads container
3. **LangGraph executes agents**:
   - Orchestrator routes to specialized agent
   - Specialist agent calls MCP tools
   - MCP server queries Cosmos DB with vector search
   - Results flow back through agent → orchestrator
4. **Response extracted** → Only last user + last assistant message
5. **Stored in Cosmos DB** → messages container
6. **Returned to user** → JSON response

---

## Environment Setup

### Prerequisites
- Python 3.11+
- Azure Cosmos DB account (with vector search enabled)
- Azure OpenAI deployment (GPT-4o, text-embedding-3-large)
- Port 8000 (FastAPI) and 8080 (MCP server) available

### Environment Variables (.env file location)
**CRITICAL**: Place `.env` file in `travel-assistant/python/.env`

```bash
# Azure Cosmos DB
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key-here
COSMOS_DATABASE_NAME=TravelAssistant

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.eastus.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# MCP Server
MCP_SERVER_BASE_URL=http://localhost:8080
MCP_AUTH_TOKEN=your-secret-token-here

# Application
LOG_LEVEL=INFO
```

### Installation
```bash
cd travel-assistant/python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Starting the Services

**Terminal 1 - MCP Server:**
```bash
cd travel-assistant/python
python -m src.app.services.mcp_http_server
# Should start on http://0.0.0.0:8080
```

**Terminal 2 - FastAPI Server:**
```bash
cd travel-assistant/python
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

---

## Key Components

### 1. FastAPI Server (`travel_agents_api.py`)
- **Lines 1-50**: Environment loading with explicit path handling
- **Lines 84-192**: Pydantic models (Thread, Message, Trip, Memory, Place)
- **Lines 245-269**: Agent initialization on startup
- **Lines 330-1296**: 40+ REST endpoints organized by tags
- **Lines 650-682**: `extract_relevant_messages()` - filters LangGraph messages

**Key Functions:**
- `get_chat_completion()`: Main endpoint for agent interaction
- `extract_relevant_messages()`: Filters messages to only last user + last assistant
- `ensure_agents_initialized()`: Lazy initialization of LangGraph agents

### 2. MCP HTTP Server (`mcp_http_server.py`)
- **Lines 1-100**: Setup, authentication, environment loading
- **Lines 427-545**: `discover_places` tool implementation
- **Lines 470-490**: Filter parsing with defensive list→string conversion
- **Lines 547-620**: `store_user_memory` tool
- **Lines 622-690**: `recall_memories` tool

**Critical Fix (Lines 470-490):**
```python
# Parse filters - convert list to string if needed (defensive programming)
place_type = filters.get("type") if filters else None
if isinstance(place_type, list):
    if place_type:
        logger.warning(f"⚠️  place_type passed as list {place_type}, using first element")
        place_type = place_type[0]
    else:
        place_type = None

# Handle pipe-separated types (e.g. "restaurant|cafe") - take first one
if place_type and "|" in place_type:
    types = place_type.split("|")
    logger.warning(f"⚠️  place_type contains pipe-separated values {types}, using first: '{types[0]}'")
    place_type = types[0]
```

### 3. LangGraph Agents (`travel_agents.py`)
- **Lines 1-150**: Agent setup, tool definitions
- **Lines 193-202**: Tool lists for each agent
- **Lines 361-500**: Agent call functions with logging
- **Lines 550-809**: Graph construction and execution

**Agent Flow:**
```
User Message → Orchestrator → [Specialist Agent] → Orchestrator → Response
                    ↓
        (Hotel/Dining/Activity/Itinerary/Summarizer)
                    ↓
            MCP Tools (discover_places, recall_memories, store_user_memory)
```

### 4. Cosmos DB Layer (`azure_cosmos_db.py`)
- **Lines 1-100**: Connection setup, container initialization
- **Lines 487-555**: `query_places()` - vector search with filters
- **Lines 310-380**: `query_memories()` - retrieve user preferences
- **Lines 150-250**: Thread management (create, get, update)

**Vector Search Query (Lines 525-540):**
```sql
SELECT TOP 5 c.geoScopeId, c.name, c.type, c.description, c.tags, 
c.accessibility, c.hours, c.neighborhood, c.priceTier, c.rating
FROM c 
WHERE c.geoScopeId = @geoScope 
  AND c.type = @type 
  AND VectorDistance(c.embedding, @referenceVector) > 0.075
ORDER BY VectorDistance(c.embedding, @referenceVector)
```

---

## Bugs Fixed & Solutions

### Bug #1: Port 8000 Already in Use
**Error:**
```
OSError: [Errno 48] Address already in use
```

**Root Cause:** Previous uvicorn processes not terminated properly

**Solution:**
```bash
# Kill all uvicorn processes
pkill -9 -f "uvicorn.*travel_agents_api"

# Verify processes are gone
ps aux | grep -E "(uvicorn|python.*travel)" | grep -v grep

# Restart server
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

**Prevention:** Always use Ctrl+C to stop servers gracefully

---

### Bug #2: Duplicate Orchestrator Messages
**Symptom:** API returns multiple greetings from same agent:
```json
"Hello! How can I help?"
"Hello again! What would you like to do?"
```

**Root Cause:** `extract_relevant_messages()` was capturing ALL intermediate messages from LangGraph execution cycles (each agent transition creates new messages)

**Solution:** Modified `extract_relevant_messages()` in `travel_agents_api.py` (lines 650-682):
```python
def extract_relevant_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Extract only the LAST user message and LAST assistant message"""
    result = []
    
    # Find last HumanMessage
    last_human = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human = msg
            break
    
    # Find last AIMessage
    last_ai = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content.strip():
            last_ai = msg
            break
    
    # Return only these two messages
    if last_human:
        result.append({"role": "user", "content": last_human.content})
    if last_ai:
        result.append({"role": "assistant", "content": last_ai.content})
    
    return result
```

**Why this works:** LangGraph creates intermediate messages for each agent call, but user only needs the final response.

---

### Bug #3: MCP Server Token/Embedding Errors
**Error:**
```
400 BadRequest: Invalid model name for embedding
```

**Root Cause:** MCP server not loading `.env` file from correct location

**Solution:** Added explicit path loading in `travel_agents_api.py` (lines 31-42):
```python
# Load environment variables with explicit path
current_file = Path(__file__)
python_dir = current_file.parent.parent.parent  # Navigate to python/ directory
env_file = python_dir / '.env'

if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"✅ Loaded .env from: {env_file}")
else:
    print(f"⚠️  No .env file found at: {env_file}")

# Verify critical environment variables
mcp_token = os.getenv("MCP_AUTH_TOKEN")
mcp_url = os.getenv("MCP_SERVER_BASE_URL", "http://localhost:8080")
print(f"🔐 MCP_AUTH_TOKEN: {'SET (' + mcp_token[:8] + '...)' if mcp_token else 'NOT SET'}")
print(f"🌐 MCP_SERVER_BASE_URL: {mcp_url}")
```

**Also updated MCP server** to load from same location with explicit path.

---

### Bug #4: Thread activeAgent Validation Error
**Error:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Thread
activeAgent
  Input should be a valid string [type=string_type, input_value=None]
```

**Root Cause:** Existing threads in Cosmos DB had `activeAgent: null`, but Pydantic model required `str`

**Solution:** Changed Thread model (line 91 in `travel_agents_api.py`):
```python
# BEFORE:
activeAgent: str = "unknown"

# AFTER:
activeAgent: Optional[str] = "unknown"
```

**Why:** Cosmos DB documents created before this field was added have `null` values. Making it `Optional[str]` allows both `null` and string values.

---

### Bug #5: Hotel Search Returns Zero Results (List vs String)
**Symptom:**
```
INFO:azure_cosmos_db:     @type: ['hotel']
INFO:azure_cosmos_db:✅ Returned 0 items from Cosmos DB
```

**Root Cause:** Hotel agent passing `filters={"type": ["hotel"]}` (list), but SQL query uses `c.type = @type` which expects string. `c.type = ['hotel']` never matches `c.type = "hotel"`.

**Solution:** Added defensive conversion in `mcp_http_server.py` (lines 470-478):
```python
place_type = filters.get("type") if filters else None
if isinstance(place_type, list):
    if place_type:
        logger.warning(f"⚠️  place_type passed as list {place_type}, using first element")
        place_type = place_type[0]
    else:
        place_type = None
```

**Design Decision:** Keep `place_type` as string-only (not list) because:
- Each specialized agent searches ONE type
- Better UX (users search one category at a time)
- Simpler code
- Multi-type scenarios should use tags instead

---

### Bug #6: Restaurant Search Returns Zero Results (Pipe-Separated Values)
**Symptom:**
```
INFO:azure_cosmos_db:     @type: restaurant|cafe
INFO:azure_cosmos_db:✅ Returned 0 items from Cosmos DB
```

**Root Cause:** Dining agent prompt instructed it to use `type="restaurant|cafe"`, but SQL query `c.type = @type` expects exact string match. `c.type = "restaurant|cafe"` never matches documents where `c.type = "restaurant"`.

**Solution 1:** Updated dining agent prompt (`dining_agent.prompty` line 15):
```diff
- 1. **Search Restaurants**: Use `discover_places` with type="restaurant|cafe" to find dining options
+ 1. **Search Restaurants**: Use `discover_places` with type="restaurant" to find dining options
```

**Solution 2:** Added defensive parsing in `mcp_http_server.py` (lines 478-482):
```python
# Handle pipe-separated types (e.g. "restaurant|cafe") - take first one
if place_type and "|" in place_type:
    types = place_type.split("|")
    logger.warning(f"⚠️  place_type contains pipe-separated values {types}, using first: '{types[0]}'")
    place_type = types[0]
```

**Why both fixes:** Prompt fix prevents issue at source; defensive code protects against future mistakes.

---

## Configuration Reference

### Port Assignments
- **8000**: FastAPI server (REST API)
- **8080**: MCP HTTP server (tool execution)
- **443**: Azure Cosmos DB (HTTPS)
- **443**: Azure OpenAI (HTTPS)

### Cosmos DB Containers
```
Database: TravelAssistant

Containers:
1. places
   - Partition Key: /geoScopeId
   - Documents: 200 (hotels, restaurants, attractions)
   - Vector Index: embedding (1024 dimensions)
   - Used by: discover_places tool

2. threads
   - Partition Key: /tenantId
   - Documents: User conversation threads
   - Fields: threadId, tenantId, userId, title, activeAgent, lastMessageAt
   - Used by: Thread management endpoints

3. messages
   - Partition Key: /threadId
   - Documents: Chat messages
   - Fields: messageId, threadId, role, content, timestamp
   - Used by: Message history endpoints

4. trips
   - Partition Key: /userId
   - Documents: Itineraries
   - Fields: tripId, userId, destination, startDate, endDate, days[]
   - Used by: Trip management endpoints

5. memories
   - Partition Key: /userId
   - Documents: User preferences
   - Fields: memoryId, userId, category, key, value, facet, ttl
   - Used by: recall_memories, store_user_memory tools
```

### Azure OpenAI Configuration
```python
# Model Deployments
CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-large"
API_VERSION = "2024-12-01-preview"

# Embedding Dimensions
VECTOR_SIZE = 1024  # text-embedding-3-large produces 1024-dim vectors

# Vector Search Threshold
SIMILARITY_THRESHOLD = 0.075  # VectorDistance > 0.075
```

---

## API Endpoints

### Health & Status
```bash
GET  /                     # Health check
GET  /health/ready         # Readiness probe (checks agent initialization)
GET  /status               # Detailed system status
```

### Thread Management
```bash
POST   /tenant/{tenantId}/user/{userId}/threads                        # Create thread
GET    /tenant/{tenantId}/user/{userId}/threads                        # List threads
GET    /tenant/{tenantId}/user/{userId}/threads/{threadId}             # Get thread details
GET    /tenant/{tenantId}/user/{userId}/threads/{threadId}/messages    # Get messages
PATCH  /tenant/{tenantId}/user/{userId}/threads/{threadId}             # Rename thread
DELETE /tenant/{tenantId}/user/{userId}/threads/{threadId}             # Delete thread
```

### Chat Completion (Main Endpoint)
```bash
POST /tenant/{tenantId}/user/{userId}/threads/{threadId}/completion
Content-Type: application/json

"What hotels are available in Rome?"

# Response:
{
  "threadId": "thread_abc123",
  "messages": [
    {"role": "user", "content": "What hotels are available in Rome?"},
    {"role": "assistant", "content": "Here are 5 hotels in Rome: ..."}
  ],
  "activeAgent": "Hotel"
}
```

### Trip Management
```bash
GET    /tenant/{tenantId}/user/{userId}/trips                         # List trips
POST   /tenant/{tenantId}/user/{userId}/trips                         # Create trip
GET    /tenant/{tenantId}/user/{userId}/trips/{tripId}                # Get trip
PUT    /tenant/{tenantId}/user/{userId}/trips/{tripId}                # Update trip
DELETE /tenant/{tenantId}/user/{userId}/trips/{tripId}                # Delete trip
```

### Memory Management
```bash
GET    /tenant/{tenantId}/user/{userId}/memories                      # List memories
POST   /tenant/{tenantId}/user/{userId}/memories                      # Create memory
DELETE /tenant/{tenantId}/user/{userId}/memories/{memoryId}           # Delete memory
```

### Places Discovery
```bash
POST /tenant/{tenantId}/user/{userId}/places/search
Content-Type: application/json

{
  "geoScope": "rome",
  "placeTypes": ["hotel"],
  "searchEmbedding": "luxury hotels near colosseum",
  "topK": 5
}
```

### Debug & Analytics
```bash
GET /tenant/{tenantId}/user/{userId}/threads/{threadId}/debug         # Debug logs
GET /tenant/{tenantId}/user/{userId}/analytics                        # User analytics
```

---

## Agent System

### Agent Types

#### 1. Orchestrator
**Role:** Routes user requests to specialized agents

**Capabilities:**
- Analyzes user intent
- Routes to appropriate specialist (Hotel, Dining, Activity, Itinerary)
- Handles general questions
- No MCP tools (pure routing logic)

**Transfer Logic:**
- "hotels" → Hotel Agent
- "restaurants" → Dining Agent  
- "attractions" → Activity Agent
- "itinerary" → Itinerary Generator
- Unknown → Stays with Orchestrator

---

#### 2. Hotel Agent
**Role:** Search hotels, store accommodation preferences

**Tools:**
- `discover_places` (type="hotel")
- `store_user_memory` (category="hotel")
- `recall_memories` (category="hotel")

**Memory Keys:**
- `budget_range`: e.g., "$100-$200/night"
- `amenities_pool`: "required"
- `accessibility_wheelchair`: "required"
- `location_downtown`: "preferred"

**Prompt Location:** `src/app/prompts/hotel_agent.prompty`

---

#### 3. Dining Agent
**Role:** Search restaurants, store dining preferences

**Tools:**
- `discover_places` (type="restaurant")
- `store_user_memory` (category="dining")
- `recall_memories` (category="dining")

**Memory Keys:**
- `dietary_vegetarian`: "required"
- `cuisine_italian`: "preferred"
- `seating_outdoor`: "preferred"
- `meal_timing_late_dinner`: "8-10pm"

**Prompt Location:** `src/app/prompts/dining_agent.prompty`

**CRITICAL FIX:** Updated line 15 to use `type="restaurant"` (not `type="restaurant|cafe"`)

---

#### 4. Activity Agent
**Role:** Search attractions, store activity preferences

**Tools:**
- `discover_places` (type="attraction")
- `store_user_memory` (category="activity")
- `recall_memories` (category="activity")

**Memory Keys:**
- `interest_art`: "preferred"
- `interest_history`: "high"
- `accessibility_wheelchair`: "required"
- `pace_leisurely`: "preferred"

**Prompt Location:** `src/app/prompts/activity_agent.prompty`

---

#### 5. Itinerary Generator
**Role:** Synthesize selections into day-by-day plans

**Tools:**
- `get_thread_context` (retrieve all selections from conversation)
- `discover_places` (fill gaps in itinerary)
- `store_user_memory` (category="trip")
- `recall_memories` (category="trip")

**Output Format:**
```
Day 1: Rome Historic Center
- Morning: Colosseum tour (3 hours)
- Lunch: Trattoria il Pommidoro (1 hour)
- Afternoon: Roman Forum (2 hours)
- Dinner: Margutta RistorArte (2 hours)
- Evening: Hotel check-in at Hotel Artemide

Day 2: Vatican & Trastevere
...
```

**Prompt Location:** `src/app/prompts/itinerary_agent.prompty`

---

#### 6. Summarizer
**Role:** Compress conversation history (auto-triggered)

**When Triggered:**
- Conversation exceeds token limit (~8,000 tokens)
- Too many messages in thread (>20 messages)

**Process:**
1. Analyzes full conversation history
2. Extracts key decisions, preferences, selections
3. Creates condensed summary
4. Replaces old messages with summary

**Prompt Location:** `src/app/prompts/summarizer_agent.prompty`

---

### Agent Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User: "Find hotels in Rome"              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Orchestrator   │
                   │  (Analyzes)     │
                   └────────┬────────┘
                            │
                     Intent: "hotel"
                            │
                            ▼
                   ┌─────────────────┐
                   │  Hotel Agent    │◄─────────┐
                   └────────┬────────┘          │
                            │                   │
                    ┌───────┴────────┐          │
                    │                │          │
                    ▼                ▼          │
          ┌──────────────┐  ┌──────────────┐   │
          │recall_memories│  │discover_places│  │
          │ (Preferences) │  │ (Vector Search)│ │
          └──────┬────────┘  └───────┬───────┘  │
                 │                   │          │
                 └────────┬──────────┘          │
                          │                     │
                    ┌─────▼─────────┐           │
                    │ 5 hotels found│           │
                    └─────┬─────────┘           │
                          │                     │
              ┌───────────┴──────────┐          │
              │                      │          │
              ▼                      ▼          │
    ┌──────────────────┐   ┌──────────────────┐│
    │store_user_memory │   │Present results   ││
    │ (Save preference)│   │to user           ││
    └──────────────────┘   └────────┬─────────┘│
                                    │          │
                            User chooses hotel │
                                    │          │
                                    ▼          │
                          ┌──────────────────┐ │
                          │"Add to itinerary"│ │
                          └────────┬─────────┘ │
                                   │           │
                    transfer_to_itinerary_generator
                                   │           │
                                   ▼           │
                          ┌─────────────────┐  │
                          │Itinerary        │  │
                          │Generator Agent  │  │
                          └─────────────────┘  │
                                                │
                          Back to Orchestrator ─┘
```

---

## Database Schema

### Places Container (Sample Document)
```json
{
  "id": "place_colosseum_001",
  "geoScopeId": "rome",
  "type": "attraction",
  "name": "Colosseum",
  "description": "Ancient Roman amphitheater, iconic landmark...",
  "neighborhood": "Monti",
  "rating": 4.8,
  "priceTier": "budget",
  "tags": ["historic", "unesco", "must-see", "photography"],
  "accessibility": ["wheelchair-accessible", "audio-guide"],
  "hours": {
    "monday": "09:00-19:00",
    "tuesday": "09:00-19:00"
  },
  "embedding": [0.123, -0.456, 0.789, ...]  // 1024 dimensions
}
```

### Threads Container (Sample Document)
```json
{
  "id": "thread_abc123",
  "threadId": "thread_abc123",
  "tenantId": "test1",
  "userId": "test2",
  "title": "Rome Trip Planning",
  "activeAgent": "Hotel",
  "createdAt": "2025-10-16T10:30:00Z",
  "lastMessageAt": "2025-10-16T12:45:00Z",
  "messageCount": 8
}
```

### Messages Container (Sample Document)
```json
{
  "id": "msg_xyz789",
  "messageId": "msg_xyz789",
  "threadId": "thread_abc123",
  "role": "assistant",
  "content": "Here are 5 hotels in Rome that match your criteria...",
  "timestamp": "2025-10-16T12:45:00Z",
  "metadata": {
    "agent": "Hotel",
    "toolCalls": ["recall_memories", "discover_places"]
  }
}
```

### Memories Container (Sample Document)
```json
{
  "id": "mem_diet_001",
  "memoryId": "mem_diet_001",
  "tenantId": "test1",
  "userId": "test2",
  "category": "dining",
  "key": "dietary_vegetarian",
  "value": "required",
  "facet": "dining",
  "memoryType": "declarative",
  "createdAt": "2025-10-16T10:00:00Z",
  "embedding": [0.234, -0.567, 0.890, ...],  // 1024 dimensions
  "ttl": null  // No expiration for declarative memories
}
```

### Trips Container (Sample Document)
```json
{
  "id": "trip_rome_2025",
  "tripId": "trip_rome_2025",
  "tenantId": "test1",
  "userId": "test2",
  "destination": "Rome, Italy",
  "startDate": "2025-11-01",
  "endDate": "2025-11-05",
  "status": "planning",
  "days": [
    {
      "dayNumber": 1,
      "date": "2025-11-01",
      "morning": {
        "activity": "Colosseum tour",
        "time": "09:00-12:00",
        "placeId": "place_colosseum_001"
      },
      "lunch": {
        "activity": "Trattoria il Pommidoro",
        "time": "12:30-13:30",
        "placeId": "place_trattoria_003"
      },
      "afternoon": {
        "activity": "Roman Forum",
        "time": "14:00-16:00",
        "placeId": "place_forum_002"
      },
      "dinner": {
        "activity": "Margutta RistorArte",
        "time": "19:00-21:00",
        "placeId": "place_margutta_005"
      },
      "accommodation": {
        "activity": "Hotel Artemide",
        "placeId": "place_hotel_artemide_010"
      }
    }
  ],
  "createdAt": "2025-10-16T12:00:00Z"
}
```

---

## Common Issues & Troubleshooting

### Issue: "Address already in use" on port 8000 or 8080
**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find processes using the port
lsof -ti:8000  # or :8080

# Kill all uvicorn processes
pkill -9 -f "uvicorn.*travel_agents_api"

# Kill MCP server
pkill -f "mcp_http_server"

# Restart services
cd travel-assistant/python
python -m src.app.services.mcp_http_server &  # Port 8080
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000
```

---

### Issue: MCP server returns 401 Unauthorized
**Symptoms:**
```
ERROR: MCP server returned 401: Unauthorized
```

**Solution:**
1. Check `.env` file exists in `travel-assistant/python/.env`
2. Verify `MCP_AUTH_TOKEN` is set and matches between:
   - FastAPI server (reads from .env)
   - MCP server (reads from .env)
3. Restart both servers after updating token

---

### Issue: Vector search returns 0 results
**Symptoms:**
```
INFO:azure_cosmos_db:✅ Returned 0 items from Cosmos DB
WARNING:azure_cosmos_db:⚠️  Query returned 0 items!
```

**Checklist:**
1. **Check geoScopeId exists:** Query Cosmos DB directly for documents with matching `geoScopeId`
2. **Check place type:** Ensure `c.type` matches exactly (e.g., "hotel" not "hotels", "restaurant" not "restaurant|cafe")
3. **Check vector threshold:** Default is 0.075, might be too strict. Try lowering to 0.05
4. **Check embedding model:** Must use `text-embedding-3-large` (1024 dimensions)
5. **Check data exists:** Verify 200 documents in places container

**Debug query in Azure Portal:**
```sql
SELECT * 
FROM c 
WHERE c.geoScopeId = "rome" 
  AND c.type = "hotel"
```

---

### Issue: Agent responses are duplicated or too verbose
**Symptoms:**
- Multiple greetings from same agent
- Full conversation history repeated in response

**Solution:**
Already fixed in `extract_relevant_messages()` (lines 650-682 of `travel_agents_api.py`). Ensure you're using latest version that filters to only last user + last assistant message.

---

### Issue: Pydantic validation errors on Thread model
**Symptoms:**
```
ValidationError: activeAgent - Input should be a valid string
```

**Solution:**
Ensure Thread model uses `Optional[str]` for fields that might be `null` in existing documents:
```python
activeAgent: Optional[str] = "unknown"
```

---

### Issue: Embedding generation fails with 400 BadRequest
**Symptoms:**
```
azure.core.exceptions.HttpResponseError: 400 BadRequest
The embedding model 'text-embedding-ada-002' is not valid
```

**Solution:**
1. Check `.env` has correct embedding model:
   ```
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
   ```
2. Verify deployment exists in Azure OpenAI Studio
3. Check API version is recent: `AZURE_OPENAI_API_VERSION=2024-12-01-preview`
4. Restart MCP server after updating .env

---

### Issue: Type mismatch in discover_places (list vs string)
**Symptoms:**
```
@type: ['hotel']  # List instead of string
```

**Solution:**
Already fixed in `mcp_http_server.py` (lines 470-490) with defensive list→string conversion. Ensure MCP server is restarted with latest code.

---

### Issue: Pipe-separated values in type filter
**Symptoms:**
```
@type: restaurant|cafe  # String with pipe
```

**Solution:**
1. **Prompt fix:** Update agent prompt to use single type (e.g., `type="restaurant"`)
2. **Defensive code:** Already added in `mcp_http_server.py` to split on `|` and take first value
3. Restart MCP server

---

## Development Workflow

### Daily Development
```bash
# 1. Start MCP server (Terminal 1)
cd travel-assistant/python
source venv/bin/activate
python -m src.app.services.mcp_http_server

# 2. Start FastAPI server (Terminal 2)
cd travel-assistant/python
source venv/bin/activate
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000

# 3. Open Swagger UI
# Browser: http://localhost:8000/docs

# 4. Test endpoints via Swagger or curl
curl -X POST "http://localhost:8000/tenant/test1/user/test2/threads" \
  -H "Content-Type: application/json"

curl -X POST "http://localhost:8000/tenant/test1/user/test2/threads/THREAD_ID/completion" \
  -H "Content-Type: application/json" \
  -d '"recommend hotels in rome"'
```

### Making Changes

**If you modify agent prompts:**
1. Edit `.prompty` files in `src/app/prompts/`
2. Restart FastAPI server (it reloads prompts on startup)
3. Test via Swagger UI

**If you modify MCP server:**
1. Edit `mcp_http_server.py`
2. Kill MCP server: `pkill -f "mcp_http_server"`
3. Restart: `python -m src.app.services.mcp_http_server`
4. Test via API

**If you modify FastAPI endpoints:**
1. Edit `travel_agents_api.py`
2. Uvicorn auto-reloads (if using `--reload` flag)
3. Check terminal for reload confirmation
4. Test via Swagger UI

**If you modify Cosmos DB queries:**
1. Test query in Azure Portal first
2. Update `azure_cosmos_db.py`
3. Restart FastAPI server
4. Test via API

### Adding New Agents

1. **Create prompt file:** `src/app/prompts/new_agent.prompty`
2. **Define tools:** Add to `travel_agents.py` tool lists
3. **Add transfer functions:** Create `transfer_to_new_agent()` and `call_new_agent()`
4. **Update graph:** Add node to `build_agent_graph()`
5. **Update agent mapping:** Add to `agent_mapping` dict in `travel_agents_api.py`
6. **Test:** Create thread, send message, verify routing

---

## Testing Guide

### Unit Testing Places Search
```bash
# Test via Swagger UI:
POST /tenant/test1/user/test2/places/search
{
  "geoScope": "rome",
  "placeTypes": ["hotel"],
  "searchEmbedding": "luxury hotels near spanish steps",
  "topK": 5
}

# Expected: 5 hotels returned with embeddings, ratings, descriptions
```

### Integration Testing Agent Flow
```bash
# 1. Create thread
POST /tenant/test1/user/test2/threads
# Returns: {"threadId": "thread_abc123", ...}

# 2. Send message
POST /tenant/test1/user/test2/threads/thread_abc123/completion
Body: "recommend hotels in rome"

# Expected flow:
# - Orchestrator receives message
# - Routes to Hotel Agent
# - Hotel Agent calls recall_memories (returns empty for new user)
# - Hotel Agent calls discover_places (returns 5 hotels)
# - Hotel Agent responds with list
# - Response contains only last user + last assistant message

# 3. Verify messages stored
GET /tenant/test1/user/test2/threads/thread_abc123/messages
# Should show user message + assistant response

# 4. Follow-up message
POST /tenant/test1/user/test2/threads/thread_abc123/completion
Body: "I prefer vegetarian restaurants"

# Expected:
# - Orchestrator routes to Dining Agent
# - Dining Agent stores preference via store_user_memory
# - Dining Agent confirms storage
```

### Testing Memory Persistence
```bash
# 1. Store preference
POST /tenant/test1/user/test2/threads/THREAD_ID/completion
Body: "I'm vegetarian and prefer outdoor seating"

# 2. Check memory stored
GET /tenant/test1/user/test2/memories
# Should show:
# - dietary_vegetarian: required
# - seating_outdoor: preferred

# 3. New thread, test recall
POST /tenant/test1/user/test2/threads  # Create new thread
POST /tenant/test1/user/test2/threads/NEW_THREAD/completion
Body: "find restaurants in barcelona"

# Expected:
# - Dining Agent recalls memories
# - Applies vegetarian + outdoor filters
# - Returns matching restaurants
```

### Load Testing
```bash
# Use Apache Bench or similar
ab -n 100 -c 10 -p message.json -T application/json \
  http://localhost:8000/tenant/test1/user/test2/threads/THREAD_ID/completion

# Monitor:
# - Response times
# - Error rates
# - Cosmos DB RU consumption
# - OpenAI API latency
```

---

## Deployment Notes

### Environment Variables for Production
```bash
# Required
COSMOS_ENDPOINT=https://prod-cosmos.documents.azure.com:443/
COSMOS_KEY=<production-key>
AZURE_OPENAI_ENDPOINT=https://prod-openai.eastus.openai.azure.com/
AZURE_OPENAI_API_KEY=<production-key>

# Security
MCP_AUTH_TOKEN=<strong-random-token>  # Generate with: openssl rand -hex 32

# Logging
LOG_LEVEL=WARNING  # Less verbose in production

# Optional: Azure Monitor
APPLICATIONINSIGHTS_CONNECTION_STRING=<app-insights-connection-string>
```

### Production Checklist
- [ ] Environment variables secured (Azure Key Vault)
- [ ] CORS origins restricted (not `*`)
- [ ] Rate limiting enabled
- [ ] Authentication/authorization implemented
- [ ] Logging to Azure Monitor configured
- [ ] Health check endpoints exposed for load balancer
- [ ] Cosmos DB throughput scaled appropriately
- [ ] OpenAI quotas/limits verified
- [ ] Container images built and pushed
- [ ] CI/CD pipeline configured

### Docker Deployment

```dockerfile
# Dockerfile (example)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src/
COPY .env .env

# Expose ports
EXPOSE 8000 8080

# Start both services (use supervisor or separate containers)
CMD ["uvicorn", "src.app.travel_agents_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment
```yaml
# deployment.yaml (example)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: travel-assistant-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: travel-assistant
  template:
    metadata:
      labels:
        app: travel-assistant
    spec:
      containers:
      - name: api
        image: <your-registry>/travel-assistant:latest
        ports:
        - containerPort: 8000
        env:
        - name: COSMOS_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: cosmos-secrets
              key: endpoint
        - name: COSMOS_KEY
          valueFrom:
            secretKeyRef:
              name: cosmos-secrets
              key: key
        livenessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Performance Optimization

### Cosmos DB
- **Indexing:** Ensure vector index on `embedding` field
- **Partition strategy:** Use `geoScopeId` for places, `userId` for memories/trips
- **RU optimization:** Monitor RU consumption, adjust provisioned throughput
- **Query efficiency:** Use `TOP` clause, filter before vector search

### OpenAI API
- **Caching:** Cache embeddings for common queries
- **Batch requests:** Group multiple embeddings into single API call
- **Rate limiting:** Implement exponential backoff for 429 errors
- **Model selection:** Use GPT-4o-mini for simpler tasks

### Application
- **Connection pooling:** Reuse Cosmos DB and OpenAI clients
- **Lazy loading:** Initialize agents on first request, not startup
- **Async operations:** Use async/await for I/O operations
- **Response streaming:** Stream responses for long-running agent tasks

---

## Security Considerations

### Authentication
- **Tenant/User IDs:** Currently passed as path parameters (trust-based)
- **Production:** Implement JWT tokens, validate user identity
- **MCP Auth Token:** Use strong random token, rotate regularly

### Data Privacy
- **PII handling:** Memories may contain sensitive preferences
- **Data retention:** Implement TTL for episodic memories (90 days)
- **Encryption:** Use Cosmos DB encryption at rest
- **Network:** Use HTTPS for all external communication

### Rate Limiting
```python
# Example: FastAPI-limiter
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/completion", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def chat_completion(...):
    # Limited to 10 requests per minute per user
```

---

## Monitoring & Observability

### Key Metrics
- **API latency:** p50, p95, p99 response times
- **Agent routing:** Which agent handles most requests
- **Tool usage:** Frequency of discover_places, recall_memories, store_user_memory
- **Error rates:** 4xx, 5xx errors by endpoint
- **Cosmos DB:** RU consumption, query latency
- **OpenAI API:** Token usage, API latency, error rates

### Logging Strategy
```python
# Structured logging
logger.info("Agent invoked", extra={
    "agent": "Hotel",
    "userId": "test2",
    "threadId": "thread_abc123",
    "duration_ms": 1234
})
```

### Alerting
- **High error rates:** >1% 5xx errors
- **High latency:** p95 > 5 seconds
- **OpenAI API failures:** >5% error rate
- **Cosmos DB throttling:** 429 responses

---

## Future Improvements

### Short Term
- [ ] Add pagination to `query_places` (currently TOP 5)
- [ ] Implement conversation summarization (auto-trigger at 8k tokens)
- [ ] Add user feedback mechanism (thumbs up/down on responses)
- [ ] Support multi-type searches (e.g., "hotels and restaurants")
- [ ] Add price range filters to all place types

### Medium Term
- [ ] Implement caching layer (Redis) for common queries
- [ ] Add support for images (hotel photos, restaurant menus)
- [ ] Implement booking integration (OpenTable, Booking.com APIs)
- [ ] Add collaborative filtering (recommend based on similar users)
- [ ] Support multiple languages (i18n)

### Long Term
- [ ] Real-time availability checks
- [ ] Dynamic pricing integration
- [ ] Mobile app (iOS/Android)
- [ ] Voice interface (speech-to-text)
- [ ] AR features (camera-based place recognition)

---

## Code Review Checklist

When reviewing PRs, check:
- [ ] **Environment variables:** New variables added to .env.example
- [ ] **Error handling:** Try/except blocks for all external calls
- [ ] **Logging:** Info logs for key events, debug logs for details
- [ ] **Type hints:** All function parameters and returns typed
- [ ] **Pydantic models:** All API inputs/outputs validated
- [ ] **Tests:** Unit tests for new functions
- [ ] **Documentation:** Docstrings for new functions/classes
- [ ] **Security:** No hardcoded secrets, proper input validation
- [ ] **Performance:** No N+1 queries, efficient data structures
- [ ] **Agent prompts:** Clear instructions, examples provided

---

## Quick Reference Commands

```bash
# Start services
python -m src.app.services.mcp_http_server &
uvicorn src.app.travel_agents_api:app --reload --host 0.0.0.0 --port 8000

# Stop services
pkill -f "mcp_http_server"
pkill -f "uvicorn.*travel_agents_api"

# View logs
tail -f api.log  # If logging to file

# Test endpoint
curl -X POST "http://localhost:8000/tenant/test1/user/test2/threads/THREAD_ID/completion" \
  -H "Content-Type: application/json" \
  -d '"recommend hotels in rome"'

# Check process status
ps aux | grep -E "(uvicorn|python.*travel)" | grep -v grep

# Check port usage
lsof -ti:8000
lsof -ti:8080

# Install dependencies
pip install -r requirements.txt

# Freeze dependencies
pip freeze > requirements.txt
```

---

## Contact & Support

**Created by:** Aayush Kataria  
**Date:** October 2025  
**GitHub:** [Travel Assistant Repository]  

For questions or issues:
1. Check this DEVELOPMENT_NOTES.md first
2. Review GitHub Copilot chat history
3. Check Azure Portal for Cosmos DB/OpenAI service health
4. Review MCP server and FastAPI logs

---

**Last Updated:** October 16, 2025  
**Document Version:** 1.0  
**Status:** Production Ready ✅
