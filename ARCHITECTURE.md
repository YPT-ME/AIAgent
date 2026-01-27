# Architecture Documentation

## System Overview

RAG AI Agent is a production-ready conversational AI system that combines document retrieval with language model generation. The system is built on a modern microservices architecture with clear separation of concerns.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client Layer                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Agent Chat UI (Next.js + React)               │  │
│  │  - WebSocket connection for streaming                       │  │
│  │  - Thread management & conversation history                 │  │
│  │  - Markdown rendering with citations                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │ WebSocket (Port 3001)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      LangGraph Server                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │           Agent Orchestration (LangGraph)                  │  │
│  │  - State management                                        │  │
│  │  - Tool execution                                          │  │
│  │  - Streaming protocol                                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Security & Middleware                         │  │
│  │  - API key authentication                                  │  │
│  │  - Rate limiting (per user)                                │  │
│  │  - Input validation                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│   OpenAI API  │    │  FAISS Store   │    │  ClickHouse  │
│   - GPT-4o    │    │  - Embeddings  │    │  - Analytics │
│   - Streaming │    │  - Similarity  │    │  - Metrics   │
└───────────────┘    └────────────────┘    └──────────────┘
                             │                     │
                             ▼                     ▼
                    ┌────────────────┐    ┌──────────────┐
                    │  File System   │    │   Grafana    │
                    │  - Manifest    │    │  - Dashboard │
                    │  - Documents   │    │  - Viz       │
                    └────────────────┘    └──────────────┘
```

## Core Components

### 1. Frontend (Agent Chat UI)

**Technology**: Next.js 14, React 19, TypeScript, TailwindCSS

**Responsibilities:**
- User interface for chat interactions
- Thread management (create, list, delete)
- Real-time streaming display
- Markdown rendering with syntax highlighting
- Citation display with source documents

**Key Files:**
- `frontend/src/app/page.tsx` - Main chat interface
- `frontend/src/components/thread/` - Thread components
- `frontend/src/components/messages/` - Message rendering
- `frontend/src/lib/client.ts` - LangGraph SDK client

**Communication:**
- WebSocket connection to LangGraph Server
- Server-Sent Events (SSE) for streaming
- REST API for thread operations

### 2. Backend (LangGraph Server)

**Technology**: Python 3.11+, LangGraph, LangChain, FastAPI

**Responsibilities:**
- Agent orchestration and state management
- Tool execution (document search)
- Security and authentication
- Analytics event tracking
- Document ingestion pipeline

**Key Modules:**

#### Agent (`src/agent/`)
- `graph.py` - Main agent graph definition
  - State management
  - Tool calling logic
  - Response generation
- `security.py` - Security middleware
  - API key validation
  - Rate limiting
  - Input sanitization

#### Ingestion (`src/ingestion/`)
- `ingest.py` - Orchestration
- `loaders.py` - Document loading (PDF, Markdown)
- `chunking.py` - Text splitting strategies
- `embeddings.py` - OpenAI embedding generation
- `vectorstore.py` - FAISS index operations
- `manifest.py` - Document change tracking (SHA256)

#### Analytics (`src/analytics/`)
- `clickhouse_analytics.py` - Event tracking
- `api.py` - Analytics REST endpoints
- `init-db.sql` - Database schema

### 3. Vector Store (FAISS)

**Technology**: Facebook AI Similarity Search

**Responsibilities:**
- Store document embeddings
- Fast similarity search (< 50ms)
- Incremental updates

**Storage Structure:**
```
storage/
├── faiss/
│   ├── index.faiss        # Vector index
│   └── index.pkl          # Metadata
└── manifest.json          # Document hashes
```

**Index Strategy:**
- IndexFlatIP (Inner Product)
- Normalized vectors
- Metadata storage for filtering

### 4. Analytics (ClickHouse + Grafana)

**Technology**: ClickHouse (columnar DB), Grafana (visualization)

**Responsibilities:**
- Track all chat interactions
- Performance metrics
- User analytics
- Tool usage statistics

**Data Model:**
```sql
- chat_messages        # All messages
- response_times       # Performance metrics
- tool_calls           # Tool usage
- user_sessions        # Session tracking
- errors               # Error logging
```

**Retention:**
- 90 days TTL (configurable)
- Automatic cleanup
- Compressed storage

## Data Flow

### 1. Document Ingestion Flow

```
PDF/Markdown Files
      │
      ▼
┌──────────────┐
│ File Loader  │  (LlamaIndex)
└──────┬───────┘
      │ Extract text + metadata
      ▼
┌──────────────┐
│ Text Chunker │  (LangChain)
└──────┬───────┘
      │ Chunk size: 1000, overlap: 200
      ▼
┌──────────────┐
│  Embeddings  │  (OpenAI text-embedding-3-small)
└──────┬───────┘
      │ 1536-dim vectors
      ▼
┌──────────────┐
│ FAISS Store  │  (Save to disk)
└──────┬───────┘
      │
      ▼
┌──────────────┐
│   Manifest   │  (Track SHA256 hashes)
└──────────────┘
```

### 2. Chat Request Flow

```
User Message (UI)
      │
      ▼
┌──────────────────┐
│  LangGraph API   │  (Authentication)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Rate Limiter    │  (Check limits)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Agent Graph     │  (Process message)
└────────┬─────────┘
         │
    ┌────┴────┐
    │ Decide  │
    └────┬────┘
         │
    ┌────┴────────────┐
    │ Need documents? │
    └────┬────────┬───┘
         │ Yes    │ No
         ▼        ▼
  ┌──────────┐  ┌────────────┐
  │  FAISS   │  │   OpenAI   │
  │  Search  │  │   Direct   │
  └────┬─────┘  └─────┬──────┘
       │              │
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │  LLM Answer  │  (Generate response)
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │   Stream     │  (Send to UI)
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │  Analytics   │  (Track event)
       └──────────────┘
```

### 3. Analytics Event Flow

```
Agent Event
    │
    ▼
┌──────────────────┐
│  Middleware      │  (Capture event)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ClickHouse DB   │  (Insert async)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Grafana Query   │  (Visualize)
└──────────────────┘
```

## Security Architecture

### Authentication
- API key-based authentication
- Key stored in environment variable
- Validated on every request

### Rate Limiting
- Per-user tracking (IP-based fallback)
- 10 requests/minute default
- Redis-compatible implementation

### Input Validation
- Maximum message length: 5000 chars
- Maximum threads per user: 20
- File type validation
- Path traversal prevention

### Data Privacy
- No PII stored without consent
- Analytics data anonymizable
- Configurable retention periods

## Scalability Considerations

### Current Limits
- Single instance deployment
- In-memory FAISS index
- Local file storage

### Scaling Strategies

**Horizontal Scaling:**
- Load balancer for multiple LangGraph servers
- Shared FAISS index (NFS or S3)
- Distributed rate limiting (Redis)

**Vertical Scaling:**
- Increase container resources
- Optimize FAISS index type
- Use quantization for embeddings

**Database Scaling:**
- ClickHouse clustering
- Replicated analytics data
- Sharding by user_id

**Storage Scaling:**
- Move to S3/Azure Blob
- CDN for static assets
- Distributed FAISS (Milvus, Pinecone)

## Monitoring & Observability

### Metrics Tracked
- Response time (p50, p90, p95, p99)
- Token usage per request
- Tool call frequency
- Error rates
- User activity

### Health Checks
- LangGraph Server: `/health`
- ClickHouse: TCP 9000
- Grafana: HTTP 3002

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized with Docker logs

## Technology Choices

### Why LangGraph?
- Built-in state management
- Native streaming support
- Tool calling abstractions
- Production-ready server

### Why FAISS?
- Fast in-memory search
- No external dependencies
- Easy to get started
- Good for < 1M documents

### Why ClickHouse?
- Optimized for analytics
- Fast aggregations
- Excellent compression
- Time-series friendly

### Why Next.js?
- Server-side rendering
- API routes
- Excellent developer experience
- Production optimizations

## Deployment Patterns

### Development
- Docker Compose
- Hot reload enabled
- Debug logging
- Local storage

### Production
- Kubernetes (recommended)
- Managed databases
- Cloud storage
- HTTPS/TLS
- Secrets management
- Horizontal scaling

## Performance Characteristics

### Latency
- Document search: 50-100ms
- LLM response (first token): 500-800ms
- Full response: 2-5s (streaming)
- Analytics insert: < 10ms (async)

### Throughput
- Single instance: ~10 concurrent users
- With scaling: 100+ concurrent users
- FAISS: 1000+ queries/sec

### Storage
- FAISS index: ~1MB per 1000 documents
- ClickHouse: ~10x compression
- Manifest: < 1MB

## Future Enhancements

- [ ] Multi-modal support (images, audio)
- [ ] Advanced RAG (HyDE, re-ranking)
- [ ] User authentication (OAuth)
- [ ] Custom embedding models
- [ ] Distributed deployment
- [ ] GraphQL API
- [ ] Mobile applications
- [ ] Vector database migration (Pinecone, Weaviate)

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [ClickHouse Documentation](https://clickhouse.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
