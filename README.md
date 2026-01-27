# RAG AI Agent Monorepo

A production-ready Retrieval-Augmented Generation (RAG) AI Agent built with **LangGraph Server**, **LangChain**, **LlamaIndex**, **FAISS**, and **OpenAI**. Features the official **Agent Chat UI** from LangChain with comprehensive analytics and monitoring.

> **Perfect for learning:** This project demonstrates modern AI agent architecture, RAG implementation, and production-ready patterns for building conversational AI applications.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

## ✨ Key Features

- 🤖 **Production-Ready Agent**: LangGraph-powered agent with streaming responses
- 📚 **Smart RAG Pipeline**: Incremental document processing with FAISS vector search
- 💬 **Modern Chat UI**: Official LangChain Agent Chat interface
- 📊 **Real-Time Analytics**: ClickHouse + Grafana monitoring dashboard
- 🔒 **Enterprise Security**: API authentication, rate limiting, input validation
- 🐳 **Docker Ready**: Complete containerized deployment
- 🚀 **Easy Setup**: Single `.env` configuration for all services

## 🏗️ Architecture

See detailed architecture documentation in [ARCHITECTURE.md](ARCHITECTURE.md).

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Agent Chat UI  │────▶│  LangGraph      │────▶│   RAG Agent     │
│   (Next.js)     │ WS  │  Server         │     │   (LangGraph)   │
│   Port 3001     │◀────│  Port 2024      │◀────│                 │
└─────────────────┘     └─────────┬───────┘     └────────┬────────┘
                                  │                       │
                                  │                       ▼
        ┌─────────────────────────┼───────────────┌───────────────┐
        │                         │               │ search_docs   │
        │                         │               │    Tool       │
        │                         │               └───────┬───────┘
        ▼                         ▼                       │
┌──────────────┐         ┌──────────────┐                ▼
│   Grafana    │◀────────│  ClickHouse  │◀───────┌───────────────┐
│  Dashboards  │         │  Analytics   │        │    FAISS      │
│  Port 3002   │         │     DB       │        │ Vector Store  │
└──────────────┘         └──────────────┘        └───────┬───────┘
                                                          │
                         ┌────────────────────────────────┤
                         │                                │
                         ▼                                ▼
                 ┌───────────────┐              ┌───────────────┐
                 │   OpenAI      │              │  Ingestion    │
                 │   LLM API     │              │  Pipeline     │
                 └───────────────┘              └───────┬───────┘
                                                        │
                                                ┌───────────────┐
                                                │  PDF/MD Files │
                                                │  ./data/docs  │
                                                └───────────────┘
```

## 🚀 Features

- **LangGraph Server**: Production-ready agent server with built-in streaming support
- **Agent Chat UI**: Official LangChain chat interface with thread management
- **Document Ingestion**: Parse PDFs & Markdown, chunk text, and embed into FAISS vector store
- **Incremental Updates**: Only re-indexes documents that have changed (SHA256 hash tracking)
- **Tool-Using Agent**: Agent with `search_documents` tool for knowledge base queries
- **Streaming Responses**: Real-time token streaming via LangGraph Server protocol
- **Citations**: Returns source documents with file names and page numbers
- **Analytics Dashboard**: Real-time monitoring with ClickHouse + Grafana
- **Performance Metrics**: Track response times, token usage, tool calls, and errors
- **Security & Rate Limiting**: API key authentication, rate limiting per user
- **Production Ready**: Docker, health checks, and auto-restart policies

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API Key

## 🛠️ Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd AIAgent

# Copy and configure the SINGLE .env file (at project root)
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

**Note**: All environment variables are now centralized in the root `.env` file. No need for separate `.env` files in `backend/` or `ui/` directories.

### 2. Add Your Documents

**Important:** Add your documents BEFORE starting the services for automatic ingestion.

```bash
# Add your PDF or Markdown files to data/docs/
cp your-documents.pdf data/docs/
cp your-documentation.md data/docs/

# Supported formats: PDF (.pdf) and Markdown (.md)
```

### 3. Run with Docker Compose (Recommended)

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up --build -d
```

The services will be available at:
- **LangGraph Server**: http://localhost:2024
- **Agent Chat UI**: http://localhost:3001
- **Analytics API**: http://localhost:9081
- **Grafana Dashboard**: http://localhost:3002 (admin/admin)
- **ClickHouse**: http://localhost:8123

**Note:** Documents in `data/docs/` are automatically ingested on first startup!

### 4. Verify Ingestion (Optional)

```bash
# Check ingestion status
docker compose exec langgraph-server python -m src.ingestion.ingest --status

# Manually re-ingest documents if needed
docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs
```

## 🔧 Local Development

### Backend Setup (LangGraph Server)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp ../.env.example .env
# Edit .env and add your OPENAI_API_KEY

# Add documents first!
cp your-documents.pdf ../data/docs/

# Run ingestion
python -m src.ingestion.ingest --docs-dir ../data/docs

# Start LangGraph development server
langgraph dev
```

The LangGraph Server will be available at http://localhost:2024

### Frontend Setup (Agent Chat UI)

```bash
cd frontend

# Install dependencies
pnpm install

# Note: Environment variables are read from root .env file
# No need for separate .env.local

# Start development server
pnpm run dev
```

The UI will be available at http://localhost:3000

### Run Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_ingestion.py -v
```

### Linting & Formatting

```bash
cd backend

# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## 📁 Project Structure

```
/
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── .env.example             # Environment variables template (SINGLE FILE)
├── docker-compose.yml       # Docker orchestration
├── Makefile                 # Common commands
├── LICENSE                  # MIT License
├── CONTRIBUTING.md          # Contribution guidelines
├── SECURITY.md              # Security policy
├── ARCHITECTURE.md          # Detailed technical documentation
├── data/
│   └── docs/                # Place your PDF and Markdown files here
│
├── backend/
│   ├── pyproject.toml       # Python dependencies & config
│   ├── langgraph.json       # LangGraph Server configuration
│   ├── Dockerfile.dev       # Backend container
│   ├── system_prompt.txt    # Agent's system prompt (customize here!)
│   ├── system_prompt.example.txt  # Example system prompt template
│   ├── storage/             # FAISS index & analytics data
│   └── src/
│       ├── agent/
│       │   ├── graph.py         # LangGraph agent with tools
│       │   └── security.py      # Rate limiting & validation
│       ├── ingestion/
│       │   ├── ingest.py        # Main ingestion orchestrator
│       │   ├── loaders.py       # PDF/Markdown loaders (LlamaIndex)
│       │   ├── chunking.py      # Text chunking (LangChain)
│       │   ├── embeddings.py    # OpenAI embeddings
│       │   ├── vectorstore.py   # FAISS operations
│       │   └── manifest.py      # Document tracking manifest
│       ├── analytics/
│       │   ├── api.py           # Analytics REST API endpoints
│       │   ├── clickhouse_analytics.py  # ClickHouse integration
│       │   ├── init-db.sql      # Database schema
│       │   └── grafana-provisioning/   # Grafana dashboards
│       ├── analytics_server.py  # Standalone analytics server
│       ├── middleware/           # FastAPI middleware
│       └── config.py            # Configuration management
│
└── frontend/
    ├── src/                 # Next.js source code
    ├── components.json      # shadcn/ui configuration
    ├── Dockerfile           # Frontend container
    └── package.json         # Node dependencies
```

## 🎨 Customizing the Agent

You can customize your agent's behavior by creating your own system prompt:

```bash
# Copy the example template
cp backend/system_prompt.example.txt backend/system_prompt.txt

# Edit with your custom instructions
nano backend/system_prompt.txt

# Restart the backend to apply changes
docker compose restart langgraph-server
```

**What you can customize:**
- Agent's personality and tone
- How it handles different types of questions
- Citation formats and source references
- Specific domain knowledge or rules
- Response style and structure

If `backend/system_prompt.txt` doesn't exist, the agent will automatically use [backend/system_prompt.example.txt](backend/system_prompt.example.txt) as a fallback.

## 🔌 API Endpoints (LangGraph Server)

LangGraph Server automatically provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/runs/stream` | POST | Stream agent responses |
| `/threads` | POST | Create conversation thread |
| `/threads/{thread_id}` | GET | Get thread details |
| `/threads/{thread_id}/runs` | POST | Start a new run |

See the [LangGraph Server Documentation](https://langchain-ai.github.io/langgraph/cloud/quick_start/) for full API reference.

## 🔄 How It Works

### Document Ingestion Pipeline

1. **PDF Loading**: LlamaIndex PDFReader extracts text with page metadata
2. **Chunking**: LangChain RecursiveCharacterTextSplitter creates chunks
3. **Embedding**: OpenAI text-embedding-3-small generates vectors
4. **Storage**: FAISS stores vectors for fast similarity search
5. **Manifest**: SHA256 hashes track processed files for incremental updates

### RAG Agent Flow

1. **User Message**: Received via Agent Chat UI
2. **LangGraph Server**: Routes to the RAG agent graph
3. **Agent Decision**: LLM decides to use `search_documents` tool
4. **Document Retrieval**: FAISS similarity search returns relevant chunks
5. **Answer Generation**: LLM generates answer with citations
6. **Streaming Response**: Tokens streamed back to UI

## 🐳 Docker Commands

```bash
# Build and run all services
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild specific service
docker compose build langgraph-server
docker compose up langgraph-server

# Run ingestion (if not done automatically)
docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs

# Access container shell
docker compose exec langgraph-server /bin/bash
```

## 📊 Analytics & Monitoring

### Real-Time Analytics Dashboard

The project includes a comprehensive analytics system powered by ClickHouse and Grafana:

**Features:**
- Real-time message metrics and response times
- User engagement and session tracking
- Tool usage statistics
- Error monitoring and alerting
- Performance percentiles (p50, p90, p95, p99)
- Token usage tracking

**Access Grafana Dashboard:**
```bash
# Dashboard available at http://localhost:3002
# Default credentials: admin/admin
```

**Analytics API Endpoints:**
```bash
# Get metrics summary
curl http://localhost:9081/analytics/metrics/summary?hours=24

# Response time percentiles
curl http://localhost:9081/analytics/metrics/response-time

# Top active users
curl http://localhost:9081/analytics/metrics/top-users?limit=10

# Popular tools usage
curl http://localhost:9081/analytics/metrics/popular-tools

# Recent errors
curl http://localhost:9081/analytics/metrics/recent-errors?limit=50
```

**What's Tracked:**
- Chat messages (user & assistant)
- Response times and token usage
- Tool invocations and success rates
- Session duration and activity
- Errors and failures

**Storage & Performance:**
- ClickHouse columnar database
- Optimized for analytical queries
- Auto-cleanup after 90 days (TTL)
- Handles millions of events/second
- 10x+ data compression

For detailed setup instructions, see [Analytics Setup Guide](backend/src/analytics/README.md).

## �🔒 Environment Variables

**🔑 Required Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `LANGGRAPH_API_KEY` | LangGraph Server API key (min 32 chars) | - |
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:2024` |
| `NEXT_PUBLIC_ASSISTANT_ID` | Assistant ID | `rag_agent` |
| `NEXT_PUBLIC_API_KEY` | Frontend API key (same as LANGGRAPH_API_KEY) | - |

**⚙️ Configuration Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL` | Chat model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `TOP_K` | Number of documents to retrieve | `5` |
| `FAISS_INDEX_PATH` | FAISS index directory | `./storage/faiss` |
| `MANIFEST_PATH` | Manifest file path | `./storage/manifest.json` |
| `DOCS_DIR` | Documents directory | `./data/docs` |
| `PDF_DIR` | PDF documents directory | `./data/docs` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per user | `10` |
| `MAX_MESSAGE_LENGTH` | Max message length | `5000` |
| `MAX_THREADS_PER_USER` | Max threads per user | `20` |

**📊 Analytics Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `CLICKHOUSE_HOST` | ClickHouse server host | `clickhouse` |
| `CLICKHOUSE_PORT` | ClickHouse HTTP port | `8123` |
| `CLICKHOUSE_USER` | ClickHouse username | `analytics` |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | `analytics_password` |
| `CLICKHOUSE_DB` | ClickHouse database name | `analytics` |
| `ANALYTICS_ENABLED` | Enable analytics tracking | `true` |
| `GRAFANA_ADMIN_USER` | Grafana admin username | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | `admin` |

**🎨 UI Customization:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_AGENT_NAME` | Agent display name | `Agent Chat` |
| `NEXT_PUBLIC_WELCOME_MESSAGE` | Welcome message | - |
| `NEXT_PUBLIC_SHOW_TOOL_CALLS_TOGGLE` | Show tool calls toggle | `true` |
| `NEXT_PUBLIC_SHOW_FILE_UPLOAD` | Enable file upload | `true` |

## 📚 Technology Stack

### Backend
- **LangGraph**: Agent orchestration framework
- **LangGraph Server**: Production agent server
- **LangChain**: LLM application framework
- **LlamaIndex**: Document parsing
- **FAISS**: Vector similarity search
- **OpenAI**: LLM and embeddings
- **Python 3.11+**: Runtime

### Frontend
- **Agent Chat UI**: Official LangChain chat interface
- **Next.js**: React framework
- **TypeScript**: Type safety

### Analytics
- **ClickHouse**: High-performance columnar database
- **Grafana**: Visualization and monitoring platform

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration

## 🧪 Testing

```bash
cd backend

# Run unit tests
pytest tests/ -v

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_agent.py::test_search_tool -v
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🔒 Security

Security is important to us. Please review our [Security Policy](SECURITY.md) for:
- Reporting vulnerabilities
- Security best practices
- API key management
- Production security guidelines

**⚠️ Important:** Never commit your `.env` file with real API keys!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Show Your Support

If this project helped you, please:
- ⭐ Star this repository
- 🐛 Report bugs and suggest features
- 🤝 Contribute code improvements
- 📖 Share with others learning AI development

## 📞 Contact & Discussion

- **Issues**: [GitHub Issues](https://github.com/YPT-ME/AIAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YPT-ME/AIAgent/discussions)

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) - LLM application framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent orchestration
- [Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) - Official chat interface
- [LlamaIndex](https://www.llamaindex.ai/) - Document parsing
- [FAISS](https://github.com/facebookresearch/faiss) - Vector search
- [OpenAI](https://openai.com/) - LLM provider
- [ClickHouse](https://clickhouse.com/) - Analytics database
- [Grafana](https://grafana.com/) - Monitoring dashboards

---

**Built with ❤️ for learning and demonstrating modern AI agent architectures**
