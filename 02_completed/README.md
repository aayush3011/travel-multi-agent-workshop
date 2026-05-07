# Travel Multi-Agent Workshop - Complete Solution

This is the complete implementation of the Travel Multi-Agent Workshop. Here you'll find a fully functional multi-agent travel assistant system with specialized AI agents that work together using Python, LangGraph, Azure OpenAI, and Azure Cosmos DB.

## Getting Started

This complete solution demonstrates the final result of the workshop with all modules implemented. You can deploy this directly to Azure or use it as a reference while working through the workshop exercises.

Deploy the complete solution 👉  **[Deploy to Azure](../README.md#deployment-instructions-for-complete-solution-02_completed)**

📖 **[User Guide](./USER_GUIDE.md)** — how to use the travel assistant, interact with agents, manage memories, and get the best results.

## Memory layer

Memory is provided by the `agent_memory_toolkit` SDK, installed in development as an editable dependency pointing at `../AgentMemoryToolkit` (TODO: switch to the published PyPI package). The toolkit auto-creates its Cosmos DB `memories`, `counter`, and `leases` containers on first run, so no Bicep container resources are needed for memory. Every 10 chat turns, a background auto-flush produces summaries, facts, and a `user_summary`. Memory records are partitioned by `(user_id, thread_id)`; `tenantId` remains for sessions, messages, and trips, but is no longer part of memory records. Memory prompts ship inside the toolkit, so `preference_extraction.prompty`, `memory_conflict_resolution.prompty`, and `summarizer.prompty` have been removed from this repo.

## Project Structure

```
02_completed/
├── python/       # Fully implemented Python application
│   ├── data/     # Complete sample data with seed scripts
│   └── src/      # Complete application source code
├── frontend/     # Complete Angular web application
├── infra/        # Complete Azure infrastructure as code
└── mcp_server/   # Complete MCP server
```

This structure contains the complete, production-ready implementation of all workshop modules with full multi-agent functionality, memory systems, and Azure integrations.