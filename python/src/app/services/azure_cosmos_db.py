import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from langgraph_checkpoint_cosmosdb import CosmosDBSaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=False)

# Azure Cosmos DB configuration
COSMOS_DB_URL = os.getenv("COSMOSDB_ENDPOINT")
COSMOS_DB_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME", "TravelAssistant")
checkpoint_container = "checkpoints"

# Global client variables
cosmos_client = None
database = None

# Container clients - for both MCP server and agent use
threads_container = None
messages_container = None
summaries_container = None
memories_container = None
api_events_container = None
places_container = None
trips_container = None


def initialize_cosmos_client():
    """Initialize the Cosmos DB client and all containers"""
    global cosmos_client, database
    global threads_container, messages_container, summaries_container
    global memories_container, api_events_container, places_container, trips_container
    
    if cosmos_client is None:
        try:
            credential = DefaultAzureCredential()
            # cosmos_client = CosmosClient(COSMOS_DB_URL, credential=credential)
            cosmos_client = CosmosClient(COSMOS_DB_URL, COSMOS_DB_KEY)
            logger.info(f"✅ Connected to Cosmos DB successfully using DefaultAzureCredential.")
        except Exception as dac_error:
            logger.error(f"❌ Failed to authenticate using DefaultAzureCredential: {dac_error}")
            logger.warning("⚠️ Continuing without Cosmos DB client - some features may not work")
            return

        # Initialize database and containers
        try:
            database = cosmos_client.get_database_client(DATABASE_NAME)
            logger.info(f"✅ Connected to database: {DATABASE_NAME}")

            # Initialize all containers
            threads_container = database.get_container_client("threads")
            messages_container = database.get_container_client("messages")
            summaries_container = database.get_container_client("summaries")
            memories_container = database.get_container_client("memories")
            api_events_container = database.get_container_client("api_events")
            places_container = database.get_container_client("places")
            trips_container = database.get_container_client("trips")
            
            logger.info("✅ All Cosmos DB containers initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing Cosmos DB containers: {e}")
            logger.warning("⚠️ Continuing without containers - some features may not work")


# Initialize on import
try:
    initialize_cosmos_client()
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize Cosmos DB client during import: {e}")


def is_cosmos_available():
    """Check if Cosmos DB is available"""
    return all([
        threads_container, messages_container, summaries_container,
        memories_container, api_events_container, places_container, trips_container
    ])


def get_cosmos_client():
    """Return the initialized Cosmos client"""
    return cosmos_client


def get_checkpoint_saver():
    """
    Return a CosmosDBSaver for LangGraph checkpoint persistence.
    Falls back to MemorySaver if Cosmos DB is not available.
    """
    if cosmos_client is not None:
        try:
            logger.info("Using CosmosDBSaver for checkpoint persistence")
            return CosmosDBSaver(
                cosmos_client=cosmos_client,
                database_name=DATABASE_NAME,
                container_name=checkpoint_container
            )
        except Exception as e:
            logger.warning(f"Failed to create CosmosDBSaver: {e}")
    
    # Fallback to in-memory checkpointer
    logger.warning("Using MemorySaver for checkpoint persistence (data will not persist)")
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


# ============================================================================
# Agent-Specific Functions (for travel_agents.py)
# ============================================================================

def update_thread_container(thread_doc: dict):
    """
    Create or update a thread document in the threads container.
    Used for initializing threads in local testing mode.
    """
    if threads_container is None:
        logger.warning("Threads container not initialized")
        return
    
    try:
        threads_container.upsert_item(thread_doc)
        logger.info(f"Thread document upserted: {thread_doc.get('id')}")
    except Exception as e:
        logger.error(f"Error upserting thread document: {e}")
        raise


def patch_active_agent(tenantId: str, userId: str, sessionId: str, activeAgent: str):
    """
    Patch the active agent field in the threads' container.
    Uses Cosmos DB patch operation for efficiency.
    """
    if threads_container is None:
        logger.warning("Threads container not initialized")
        return
    
    try:
        operations = [
            {'op': 'replace', 'path': '/activeAgent', 'value': activeAgent}
        ]
        
        pk = [tenantId, userId, sessionId]
        threads_container.patch_item(
            item=sessionId, 
            partition_key=pk,
            patch_operations=operations
        )
        logger.info(f"Patched active agent to '{activeAgent}' for session: {sessionId}")
    except Exception as e:
        logger.error(f"Error patching active agent for tenantId: {tenantId}, userId: {userId}, sessionId: {sessionId}: {e}")
        # Don't raise - this is not critical for operation


# ============================================================================
# MCP Tool Functions (for mcp_http_server.py)
# ============================================================================

def create_thread_record(user_id: str, tenant_id: str, activeAgent: str, title: str = None) -> Dict[str, Any]:
    """Create a new thread record"""
    if not threads_container:
        raise Exception("Cosmos DB not available")
    
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    thread = {
        "id": thread_id,
        "threadId": thread_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "title": title or "New Conversation",
        "activeAgent": activeAgent,
        "createdAt": now,
        "lastActivityAt": now,
        "status": "active",
        "messageCount": 0
    }
    
    threads_container.upsert_item(thread)
    logger.info(f"✅ Created thread: {thread_id}")
    return thread


def get_thread_by_id(thread_id: str, tenant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get thread by ID"""
    if not threads_container:
        raise Exception("Cosmos DB not available")
    
    try:
        query = """
        SELECT * FROM c 
        WHERE c.threadId = @threadId 
        AND c.tenantId = @tenantId 
        AND c.userId = @userId
        """
        items = list(threads_container.query_items(
            query=query,
            parameters=[
                {"name": "@threadId", "value": thread_id},
                {"name": "@tenantId", "value": tenant_id},
                {"name": "@userId", "value": user_id}
            ],
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error getting thread: {e}")
        return None


def update_thread_activity(thread_id: str, tenant_id: str, user_id: str):
    """Update thread's last activity timestamp"""
    if not threads_container:
        return
    
    thread = get_thread_by_id(thread_id, tenant_id, user_id)
    if thread:
        thread["lastActivityAt"] = datetime.utcnow().isoformat() + "Z"
        thread["messageCount"] = thread.get("messageCount", 0) + 1
        threads_container.upsert_item(thread)


# ============================================================================
# Message Management Functions
# ============================================================================

def append_message(
    thread_id: str,
    tenant_id: str,
    user_id: str,
    role: str,
    content: str,
    tool_call: Optional[Dict] = None,
    embedding: Optional[List[float]] = None,
    keywords: Optional[List[str]] = None
) -> str:
    """Append a message to a thread"""
    if not messages_container:
        raise Exception("Cosmos DB not available")
    
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    message = {
        "id": message_id,
        "messageId": message_id,
        "threadId": thread_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "role": role,
        "content": content,
        "toolCall": tool_call,
        "embedding": embedding,
        "ts": now,
        "keywords": keywords or [],
        "superseded": False
    }
    
    messages_container.upsert_item(message)
    update_thread_activity(thread_id, tenant_id, user_id)
    
    logger.info(f"✅ Appended message: {message_id} to thread: {thread_id}")
    return message_id


def get_thread_messages(
    thread_id: str,
    tenant_id: str,
    user_id: str,
    include_superseded: bool = False
) -> List[Dict[str, Any]]:
    """Get messages for a thread"""
    if not messages_container:
        return []
    
    superseded_filter = "" if include_superseded else "AND (NOT IS_DEFINED(c.superseded) OR c.superseded = false)"
    
    query = f"""
    SELECT * FROM c 
    WHERE c.threadId = @threadId 
    AND c.tenantId = @tenantId 
    AND c.userId = @userId
    {superseded_filter}
    ORDER BY c.ts DESC
    """
    
    items = list(messages_container.query_items(
        query=query,
        parameters=[
            {"name": "@threadId", "value": thread_id},
            {"name": "@tenantId", "value": tenant_id},
            {"name": "@userId", "value": user_id}
        ],
        enable_cross_partition_query=True
    ))
    
    return items


# ============================================================================
# Summary Management Functions
# ============================================================================

def create_summary(
    thread_id: str,
    tenant_id: str,
    user_id: str,
    summary_text: str,
    span: Dict[str, str],
    embedding: Optional[List[float]] = None,
    supersedes: Optional[List[str]] = None
) -> str:
    """Create a summary and mark messages as superseded"""
    if not summaries_container or not messages_container:
        raise Exception("Cosmos DB not available")
    
    summary_id = f"summary_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    summary = {
        "id": summary_id,
        "summaryId": summary_id,
        "threadId": thread_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "span": span,
        "text": summary_text,
        "embedding": embedding,
        "createdAt": now,
        "supersedes": supersedes or []
    }
    
    summaries_container.upsert_item(summary)
    
    # Mark superseded messages
    if supersedes:
        for msg_id in supersedes:
            try:
                # Note: In production, you'd use bulk operations or patches
                # For now, using simple query + update
                query = "SELECT * FROM c WHERE c.messageId = @msgId"
                items = list(messages_container.query_items(
                    query=query,
                    parameters=[{"name": "@msgId", "value": msg_id}],
                    enable_cross_partition_query=True
                ))
                if items:
                    msg = items[0]
                    msg["superseded"] = True
                    msg["ttl"] = 2592000  # 30 days
                    messages_container.upsert_item(msg)
            except Exception as e:
                logger.error(f"Error marking message {msg_id} as superseded: {e}")
    
    logger.info(f"✅ Created summary: {summary_id} superseding {len(supersedes or [])} messages")
    return summary_id


def get_thread_summaries(
    thread_id: str,
    tenant_id: str,
    user_id: str,
) -> List[Dict[str, Any]]:
    """Get summaries for a thread"""
    if not summaries_container:
        return []
    
    query = """
    SELECT * FROM c 
    WHERE c.threadId = @threadId 
    AND c.tenantId = @tenantId 
    AND c.userId = @userId
    ORDER BY c.createdAt DESC
    """
    
    items = list(summaries_container.query_items(
        query=query,
        parameters=[
            {"name": "@threadId", "value": thread_id},
            {"name": "@tenantId", "value": tenant_id},
            {"name": "@userId", "value": user_id}
        ],
        enable_cross_partition_query=True
    ))
    
    return items


# ============================================================================
# Memory Management Functions
# ============================================================================

def store_memory(
    user_id: str,
    tenant_id: str,
    memory_type: str,
    text: str,
    facets: Dict[str, Any],
    salience: float,
    justification: str,
    embedding: Optional[List[float]] = None
) -> str:
    """Store a user memory"""
    if not memories_container:
        raise Exception("Cosmos DB not available")
    
    memory_id = f"mem_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    # Set TTL based on memory type
    ttl = None
    if memory_type == "episodic":
        ttl = 7776000  # 90 days in seconds
    
    memory = {
        "id": memory_id,
        "memoryId": memory_id,
        "userId": user_id,
        "tenantId": tenant_id,
        "memoryType": memory_type,
        "text": text,
        "facets": facets,
        "embedding": embedding,
        "salience": salience,
        "ttl": ttl,
        "justification": justification,
        "lastUsedAt": now,
        "extractedAt": now
    }
    
    memories_container.upsert_item(memory)
    logger.info(f"✅ Stored memory: {memory_id} (type: {memory_type}, salience: {salience})")
    return memory_id


def query_memories(
    user_id: str,
    tenant_id: str,
    memory_types: Optional[List[str]] = None,
    min_salience: float = 0.0,
) -> List[Dict[str, Any]]:
    """Query memories for a user"""
    if not memories_container:
        return []
    
    type_filter = ""
    if memory_types:
        type_list = ", ".join([f"'{t}'" for t in memory_types])
        type_filter = f"AND c.memoryType IN ({type_list})"
    
    query = f"""
    SELECT TOP 5 * FROM c 
    WHERE c.userId = @userId 
    AND c.tenantId = @tenantId
    AND c.salience >= @minSalience
    {type_filter}
    ORDER BY c.createdAt DESC
    """
    
    items = list(memories_container.query_items(
        query=query,
        parameters=[
            {"name": "@userId", "value": user_id},
            {"name": "@tenantId", "value": tenant_id},
            {"name": "@minSalience", "value": min_salience}
        ],
        enable_cross_partition_query=True
    ))
    
    return items


# ============================================================================
# Place Discovery Functions
# ============================================================================

def query_places(
    vectors: List[float],
    geo_scope_id: str,
    place_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    dietary: Optional[List[str]] = None,
    price_tier: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query places with filters"""
    logger.info(f"🔍 ========== QUERY_PLACES CALLED ==========")
    logger.info(f"🔍 Parameters:")
    logger.info(f"     - geo_scope_id: {geo_scope_id}")
    logger.info(f"     - place_type: {place_type}")
    logger.info(f"     - dietary: {dietary}")
    logger.info(f"     - price_tier: {price_tier}")
    logger.info(f"     - tags: {tags}")
    logger.info(f"     - vectors dimension: {len(vectors) if vectors else 'None'}")
    
    if not places_container:
        logger.error(f"❌ places_container is None! Cosmos DB not initialized properly.")
        return []
    
    logger.info(f"✅ places_container is available")

    geo_scope_id = geo_scope_id.lower().strip()
    filters = ["c.geoScopeId = @geoScope"]
    params = [{"name": "@geoScope", "value": geo_scope_id}]
    
    if place_type:
        filters.append("c.type = @type")
        params.append({"name": "@type", "value": place_type})
    
    if price_tier is not None:
        filters.append("c.priceTier = @priceTier")
        params.append({"name": "@priceTier", "value": price_tier})
    
    # Note: Complex array filters would require additional logic
    where_clause = " AND ".join(filters)
    
    query = f"""
    SELECT TOP 5 c.geoScopeId, c.name, c.type, c.description, c.tags, 
    c.accessibility, c.hours, c.neighborhood, c.priceTier, c.rating
    FROM c 
    WHERE {where_clause} AND VectorDistance(c.embedding, @referenceVector)> 0.075
    ORDER BY VectorDistance(c.embedding, @referenceVector) 
    """
    params.append({"name": "@referenceVector", "value": vectors})

    logger.info(f"📝 Cosmos DB Query:")
    logger.info(f"     {query}")
    logger.info(f"📝 Query Parameters:")
    for param in params:
        if param["name"] == "@referenceVector":
            logger.info(f"     {param['name']}: [vector array with {len(param['value'])} dimensions]")
        else:
            logger.info(f"     {param['name']}: {param['value']}")

    try:
        logger.info(f"🚀 Executing Cosmos DB query...")
        items = list(places_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        logger.info(f"✅ Query executed successfully!")
        logger.info(f"✅ Returned {len(items)} items from Cosmos DB")
        
        if items:
            logger.info(f"📍 First result: {items[0].get('name', 'N/A')} (type: {items[0].get('type', 'N/A')}, geoScopeId: {items[0].get('geoScopeId', 'N/A')})")
        else:
            logger.warning(f"⚠️  Query returned 0 items!")
            logger.warning(f"⚠️  Check if:")
            logger.warning(f"      1. Data exists for geoScopeId='{geo_scope_id}'")
            logger.warning(f"      2. place_type filter is correct: {place_type}")
            logger.warning(f"      3. Vector similarity threshold (0.075) might be too strict")
            
    except Exception as ex:
        logger.error(f"❌ Error querying places: {ex}")
        logger.error(f"❌ Exception type: {type(ex).__name__}")
        import traceback
        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        raise ex
    
    logger.info(f"🔍 ========== QUERY_PLACES COMPLETED ==========")
    return items


# ============================================================================
# Trip Management Functions
# ============================================================================

def create_trip(
    user_id: str,
    tenant_id: str,
    scope: Dict[str, str],
    dates: Dict[str, str],
    travelers: List[str],
    constraints: Dict[str, Any]
) -> str:
    """Create a new trip"""
    if not trips_container:
        raise Exception("Cosmos DB not available")
    
    trip_id = f"trip_{datetime.utcnow().strftime('%Y')}_{scope['id'][:3]}"
    
    trip = {
        "id": trip_id,
        "tripId": trip_id,
        "userId": user_id,
        "tenantId": tenant_id,
        "scope": scope,
        "dates": dates,
        "travelers": travelers,
        "constraints": constraints,
        "days": [],
        "status": "planning"
    }
    
    trips_container.upsert_item(trip)
    logger.info(f"✅ Created trip: {trip_id}")
    return trip_id


def get_trip(trip_id: str, user_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a trip by ID"""
    if not trips_container:
        return None
    
    try:
        query = """
        SELECT * FROM c 
        WHERE c.tripId = @tripId 
        AND c.userId = @userId 
        AND c.tenantId = @tenantId
        """
        items = list(trips_container.query_items(
            query=query,
            parameters=[
                {"name": "@tripId", "value": trip_id},
                {"name": "@userId", "value": user_id},
                {"name": "@tenantId", "value": tenant_id}
            ],
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error getting trip: {e}")
        return None


# ============================================================================
# API Event Functions
# ============================================================================

def record_api_event(
    thread_id: str,
    tenant_id: str,
    provider: str,
    operation: str,
    request: Dict[str, Any],
    response: Dict[str, Any],
    keywords: Optional[List[str]] = None
) -> str:
    """Record an API event"""
    if not api_events_container:
        raise Exception("Cosmos DB not available")
    
    event_id = f"api_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    event = {
        "id": event_id,
        "eventId": event_id,
        "threadId": thread_id,
        "tenantId": tenant_id,
        "provider": provider,
        "operation": operation,
        "request": request,
        "response": response,
        "ts": now,
        "keywords": keywords or []
    }
    
    api_events_container.upsert_item(event)
    logger.info(f"✅ Recorded API event: {event_id} ({provider}.{operation})")
    return event_id
