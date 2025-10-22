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
checkpoint_container = "Checkpoints"

# Global client variables
cosmos_client = None
database = None

# Container clients - for both MCP server and agent use
sessions_container = None
messages_container = None
summaries_container = None
memories_container = None
api_events_container = None
debug_logs_container = None
places_container = None
trips_container = None
users_container = None


def initialize_cosmos_client():
    """Initialize the Cosmos DB client and all containers"""
    global cosmos_client, database
    global sessions_container, messages_container, summaries_container
    global memories_container, api_events_container, debug_logs_container, places_container, trips_container, users_container
    
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

            # Initialize all containers (using PascalCase names to match Bicep)
            sessions_container = database.get_container_client("Sessions")
            messages_container = database.get_container_client("Messages")
            summaries_container = database.get_container_client("Summaries")
            memories_container = database.get_container_client("Memories")
            api_events_container = database.get_container_client("ApiEvents")
            debug_logs_container = database.get_container_client("Debug")
            places_container = database.get_container_client("Places")
            trips_container = database.get_container_client("Trips")
            users_container = database.get_container_client("Users")
            
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
        sessions_container, messages_container, summaries_container,
        memories_container, api_events_container, debug_logs_container, places_container, trips_container, users_container
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

def update_session_container(session_doc: dict):
    """
    Create or update a session document in the sessions container.
    Used for initializing sessions in local testing mode.
    """
    if sessions_container is None:
        logger.warning("Sessions container not initialized")
        return
    
    try:
        sessions_container.upsert_item(session_doc)
        logger.info(f"Session document upserted: {session_doc.get('id')}")
    except Exception as e:
        logger.error(f"Error upserting session document: {e}")
        raise


def patch_active_agent(tenantId: str, userId: str, sessionId: str, activeAgent: str):
    """
    Patch the active agent field in the sessions' container.
    Uses Cosmos DB patch operation for efficiency.
    If the field doesn't exist, it will be added instead of replaced.
    """
    if sessions_container is None:
        logger.warning("Sessions container not initialized")
        return
    
    try:
        pk = [tenantId, userId, sessionId]
        
        # Try to read the document first to check if activeAgent exists
        try:
            session_doc = sessions_container.read_item(item=sessionId, partition_key=pk)
            # Field exists, use replace
            operation = 'replace' if 'activeAgent' in session_doc else 'add'
        except:
            # Document might not exist or can't be read, try add
            operation = 'add'
        
        operations = [
            {'op': operation, 'path': '/activeAgent', 'value': activeAgent}
        ]
        
        sessions_container.patch_item(
            item=sessionId, 
            partition_key=pk,
            patch_operations=operations
        )
        logger.info(f"✅ Patched active agent to '{activeAgent}' for session: {sessionId} (operation: {operation})")
    except Exception as e:
        logger.error(f"❌ Error patching active agent for tenantId: {tenantId}, userId: {userId}, sessionId: {sessionId}: {e}")
        # Fallback: Try to update the whole document
        try:
            session_doc = sessions_container.read_item(item=sessionId, partition_key=pk)
            session_doc['activeAgent'] = activeAgent
            sessions_container.upsert_item(session_doc)
            logger.info(f"✅ Updated active agent via upsert to '{activeAgent}' for session: {sessionId}")
        except Exception as fallback_error:
            logger.error(f"❌ Fallback upsert also failed: {fallback_error}")
            # Don't raise - this is not critical for operation


# ============================================================================
# MCP Tool Functions (for mcp_http_server.py)
# ============================================================================

def create_session_record(user_id: str, tenant_id: str, activeAgent: str, title: str = None) -> Dict[str, Any]:
    """Create a new session record"""
    if not sessions_container:
        raise Exception("Cosmos DB not available")
    
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    session = {
        "id": session_id,
        "sessionId": session_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "title": title or "New Conversation",
        "activeAgent": activeAgent,
        "createdAt": now,
        "lastActivityAt": now,
        "status": "active",
        "messageCount": 0
    }
    
    sessions_container.upsert_item(session)
    logger.info(f"✅ Created session: {session_id}")
    return session


def get_session_by_id(session_id: str, tenant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID"""
    if not sessions_container:
        raise Exception("Cosmos DB not available")
    
    try:
        query = """
        SELECT * FROM c 
        WHERE c.sessionId = @sessionId 
        AND c.tenantId = @tenantId 
        AND c.userId = @userId
        """
        items = list(sessions_container.query_items(
            query=query,
            parameters=[
                {"name": "@sessionId", "value": session_id},
                {"name": "@tenantId", "value": tenant_id},
                {"name": "@userId", "value": user_id}
            ],
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return None


def update_session_activity(session_id: str, tenant_id: str, user_id: str):
    """Update session's last activity timestamp"""
    if not sessions_container:
        return
    
    session = get_session_by_id(session_id, tenant_id, user_id)
    if session:
        session["lastActivityAt"] = datetime.utcnow().isoformat() + "Z"
        session["messageCount"] = session.get("messageCount", 0) + 1
        sessions_container.upsert_item(session)


# ============================================================================
# Message Management Functions
# ============================================================================

def append_message(
    session_id: str,
    tenant_id: str,
    user_id: str,
    role: str,
    content: str,
    tool_call: Optional[Dict] = None,
    embedding: Optional[List[float]] = None,
    keywords: Optional[List[str]] = None
) -> str:
    """Append a message to a session"""
    if not messages_container:
        raise Exception("Cosmos DB not available")
    
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"
    
    message = {
        "id": message_id,
        "messageId": message_id,
        "sessionId": session_id,
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
    update_session_activity(session_id, tenant_id, user_id)
    
    logger.info(f"✅ Appended message: {message_id} to session: {session_id}")
    return message_id


def get_session_messages(
    session_id: str,
    tenant_id: str,
    user_id: str,
    include_superseded: bool = False
) -> List[Dict[str, Any]]:
    """Get messages for a session"""
    if not messages_container:
        return []
    
    superseded_filter = "" if include_superseded else "AND (NOT IS_DEFINED(c.superseded) OR c.superseded = false)"
    
    query = f"""
    SELECT * FROM c 
    WHERE c.sessionId = @sessionId 
    AND c.tenantId = @tenantId 
    AND c.userId = @userId
    {superseded_filter}
    ORDER BY c.ts DESC
    """
    
    items = list(messages_container.query_items(
        query=query,
        parameters=[
            {"name": "@sessionId", "value": session_id},
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
    session_id: str,
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
        "sessionId": session_id,
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


def get_session_summaries(
    session_id: str,
    tenant_id: str,
    user_id: str,
) -> List[Dict[str, Any]]:
    """Get summaries for a session"""
    if not summaries_container:
        return []
    
    query = """
    SELECT * FROM c 
    WHERE c.sessionId = @sessionId 
    AND c.tenantId = @tenantId 
    AND c.userId = @userId
    ORDER BY c.createdAt DESC
    """
    
    items = list(summaries_container.query_items(
        query=query,
        parameters=[
            {"name": "@sessionId", "value": session_id},
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
    constraints: Dict[str, Any],
    days: Optional[List[Dict[str, Any]]] = None,
    trip_duration: Optional[int] = None
) -> str:
    """Create a new trip"""
    if not trips_container:
        raise Exception("Cosmos DB not available")
    
    trip_id = f"trip_{datetime.utcnow().strftime('%Y')}_{scope['id'][:3]}"
    
    # Calculate trip duration from days array if not provided
    if trip_duration is None and days:
        trip_duration = len(days)
    
    trip = {
        "id": trip_id,
        "tripId": trip_id,
        "userId": user_id,
        "tenantId": tenant_id,
        "scope": scope,
        "dates": dates,
        "travelers": travelers,
        "constraints": constraints,
        "tripDuration": trip_duration,
        "days": days or [],
        "status": "planning"
    }
    
    trips_container.upsert_item(trip)
    logger.info(f"✅ Created trip: {trip_id} with {trip_duration} days")
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
# User Management Functions
# ============================================================================

def create_user(
    user_id: str,
    tenant_id: str,
    name: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    phone: Optional[str] = None,
    address: Optional[Dict[str, Any]] = None,
    email: Optional[str] = None
) -> str:
    """Create a new user"""
    if not users_container:
        raise Exception("Cosmos DB users container not available")
    
    now = datetime.utcnow().isoformat() + "Z"
    
    user = {
        "id": user_id,
        "userId": user_id,
        "tenantId": tenant_id,
        "name": name,
        "gender": gender,
        "age": age,
        "phone": phone,
        "address": address or {},
        "email": email,
        "createdAt": now
    }
    
    users_container.upsert_item(user)
    logger.info(f"✅ Created user: {user_id} ({name})")
    return user_id


def get_all_users(tenant_id: str) -> List[Dict[str, Any]]:
    """Get all users for a tenant"""
    if not users_container:
        return []
    
    try:
        query = """
        SELECT * FROM c 
        WHERE c.tenantId = @tenantId
        ORDER BY c.createdAt DESC
        """
        items = list(users_container.query_items(
            query=query,
            parameters=[
                {"name": "@tenantId", "value": tenant_id}
            ],
            enable_cross_partition_query=True
        ))
        logger.info(f"✅ Retrieved {len(items)} users for tenant: {tenant_id}")
        return items
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []


def get_user_by_id(user_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID"""
    if not users_container:
        return None
    
    try:
        query = """
        SELECT * FROM c 
        WHERE c.userId = @userId 
        AND c.tenantId = @tenantId
        """
        items = list(users_container.query_items(
            query=query,
            parameters=[
                {"name": "@userId", "value": user_id},
                {"name": "@tenantId", "value": tenant_id}
            ],
            enable_cross_partition_query=True
        ))
        if items:
            logger.info(f"✅ Retrieved user: {user_id}")
            return items[0]
        else:
            logger.warning(f"⚠️  User not found: {user_id}")
            return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None


# ============================================================================
# API Event Functions
# ============================================================================

def record_api_event(
    session_id: str,
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
        "sessionId": session_id,
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


# ============================================================================
# Debug Logs
# ============================================================================

def store_debug_log(
    session_id: str,
    tenant_id: str,
    user_id: str,
    agent_selected: str = "Unknown",
    previous_agent: str = "Unknown",
    finish_reason: str = "Unknown",
    model_name: str = "Unknown",
    system_fingerprint: str = "Unknown",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cached_tokens: int = 0,
    transfer_success: bool = False,
    tool_calls: List[Dict[str, Any]] = None,
    logprobs: Optional[Dict[str, Any]] = None,
    content_filter_results: Optional[Dict[str, Any]] = None
) -> str:
    """
    Store detailed debug log information in Cosmos DB.
    
    Args:
        session_id: Session identifier
        tenant_id: Tenant identifier
        user_id: User identifier
        agent_selected: Name of the agent that handled the request
        previous_agent: Name of the previous agent (for transfers)
        finish_reason: Reason for completion (stop, length, etc.)
        model_name: Name of the LLM model used
        system_fingerprint: System fingerprint from the model
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        total_tokens: Total tokens used
        cached_tokens: Number of cached tokens
        transfer_success: Whether agent transfer was successful
        tool_calls: List of tool calls made during execution
        logprobs: Log probabilities from the model
        content_filter_results: Content filtering results
    
    Returns:
        Debug log ID
    """
    if not debug_logs_container:
        raise Exception("Debug logs container not available")
    
    debug_log_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    property_bag = [
        {"key": "agent_selected", "value": agent_selected, "timeStamp": timestamp},
        {"key": "previous_agent", "value": previous_agent, "timeStamp": timestamp},
        {"key": "finish_reason", "value": finish_reason, "timeStamp": timestamp},
        {"key": "model_name", "value": model_name, "timeStamp": timestamp},
        {"key": "system_fingerprint", "value": system_fingerprint, "timeStamp": timestamp},
        {"key": "input_tokens", "value": input_tokens, "timeStamp": timestamp},
        {"key": "output_tokens", "value": output_tokens, "timeStamp": timestamp},
        {"key": "total_tokens", "value": total_tokens, "timeStamp": timestamp},
        {"key": "cached_tokens", "value": cached_tokens, "timeStamp": timestamp},
        {"key": "transfer_success", "value": transfer_success, "timeStamp": timestamp},
        {"key": "tool_calls", "value": str(tool_calls or []), "timeStamp": timestamp},
        {"key": "logprobs", "value": str(logprobs or {}), "timeStamp": timestamp},
        {"key": "content_filter_results", "value": str(content_filter_results or {}), "timeStamp": timestamp}
    ]
    
    debug_entry = {
        "id": debug_log_id,
        "debugLogId": debug_log_id,
        "messageId": message_id,
        "type": "debug_log",
        "sessionId": session_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "timeStamp": timestamp,
        "propertyBag": property_bag
    }
    
    debug_logs_container.upsert_item(debug_entry)
    logger.info(f"✅ Stored debug log: {debug_log_id} (agent: {agent_selected}, tokens: {total_tokens})")
    return debug_log_id


def get_debug_log(debug_log_id: str, tenant_id: str, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a debug log by ID.
    
    Args:
        debug_log_id: Debug log identifier
        tenant_id: Tenant identifier
        user_id: User identifier
        session_id: Session identifier
    
    Returns:
        Debug log document or None if not found
    """
    if not debug_logs_container:
        raise Exception("Debug logs container not available")
    
    try:
        partition_key = [tenant_id, user_id, session_id]
        item = debug_logs_container.read_item(item=debug_log_id, partition_key=partition_key)
        logger.info(f"✅ Retrieved debug log: {debug_log_id}")
        return item
    except Exception as e:
        logger.warning(f"⚠️ Debug log not found: {debug_log_id} - {e}")
        return None


def query_debug_logs(
    session_id: str,
    tenant_id: str,
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Query debug logs for a session.
    
    Args:
        session_id: Session identifier
        tenant_id: Tenant identifier
        user_id: User identifier
        limit: Maximum number of logs to return
    
    Returns:
        List of debug log documents
    """
    if not debug_logs_container:
        raise Exception("Debug logs container not available")
    
    query = f"""
    SELECT TOP {limit} *
    FROM c
    WHERE c.sessionId = @sessionId
      AND c.tenantId = @tenantId
      AND c.userId = @userId
    ORDER BY c.timeStamp DESC
    """
    
    parameters = [
        {"name": "@sessionId", "value": session_id},
        {"name": "@tenantId", "value": tenant_id},
        {"name": "@userId", "value": user_id}
    ]
    
    items = list(debug_logs_container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=False
    ))
    
    logger.info(f"✅ Retrieved {len(items)} debug logs for session {session_id}")
    return items


def get_distinct_cities(tenant_id: str) -> List[Dict[str, str]]:
    """Get distinct cities from places container"""
    if not places_container:
        return []
    
    try:
        # Query to get distinct geoScopeIds
        query = """
        SELECT DISTINCT VALUE c.geoScopeId
        FROM c
        """
        
        geo_scope_ids = list(places_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        # Create city objects with display names
        cities = []
        city_name_map = {
            "abu_dhabi": "Abu Dhabi, UAE",
            "amsterdam": "Amsterdam, Netherlands",
            "athens": "Athens, Greece",
            "auckland": "Auckland, New Zealand",
            "bangkok": "Bangkok, Thailand",
            "barcelona": "Barcelona, Spain",
            "beijing": "Beijing, China",
            "berlin": "Berlin, Germany",
            "brussels": "Brussels, Belgium",
            "budapest": "Budapest, Hungary",
            "chicago": "Chicago, USA",
            "christchurch": "Christchurch, New Zealand",
            "copenhagen": "Copenhagen, Denmark",
            "delhi": "Delhi, India",
            "dubai": "Dubai, UAE",
            "dublin": "Dublin, Ireland",
            "edinburgh": "Edinburgh, Scotland",
            "frankfurt": "Frankfurt, Germany",
            "glasgow": "Glasgow, Scotland",
            "hong_kong": "Hong Kong",
            "istanbul": "Istanbul, Turkey",
            "kuala_lumpur": "Kuala Lumpur, Malaysia",
            "lisbon": "Lisbon, Portugal",
            "london": "London, UK",
            "los_angeles": "Los Angeles, USA",
            "madrid": "Madrid, Spain",
            "manchester": "Manchester, UK",
            "melbourne": "Melbourne, Australia",
            "miami": "Miami, USA",
            "milan": "Milan, Italy",
            "mumbai": "Mumbai, India",
            "new_york": "New York, USA",
            "osaka": "Osaka, Japan",
            "oslo": "Oslo, Norway",
            "paris": "Paris, France",
            "prague": "Prague, Czech Republic",
            "reykjavik": "Reykjavik, Iceland",
            "rome": "Rome, Italy",
            "san_francisco": "San Francisco, USA",
            "seattle": "Seattle, USA",
            "seoul": "Seoul, South Korea",
            "singapore": "Singapore",
            "stockholm": "Stockholm, Sweden",
            "sydney": "Sydney, Australia",
            "tokyo": "Tokyo, Japan",
            "toronto": "Toronto, Canada",
            "vancouver": "Vancouver, Canada",
            "vienna": "Vienna, Austria",
            "zurich": "Zurich, Switzerland"
        }
        
        for geo_id in sorted(geo_scope_ids):
            display_name = city_name_map.get(geo_id, geo_id.replace("_", " ").title())
            cities.append({
                "id": geo_id,
                "name": geo_id,
                "displayName": display_name
            })
        
        logger.info(f"✅ Retrieved {len(cities)} distinct cities")
        return cities
        
    except Exception as e:
        logger.error(f"Error getting distinct cities: {e}")
        return []


