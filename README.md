# RAG AI Agent Monorepo

A production-ready Retrieval-Augmented Generation (RAG) AI Agent built with **LangGraph Server**, **LangChain**, **LlamaIndex**, **FAISS**, and **OpenAI**. Features the official **Agent Chat UI** from LangChain.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Agent Chat UI  │────▶│  LangGraph      │────▶│   RAG Agent     │
│   (Next.js)     │ WS  │  Server         │     │   (LangGraph)   │
│                 │◀────│  Port 2024      │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                │                       ▼
                                │               ┌───────────────┐
                                │               │ search_docs   │
                                │               │    Tool       │
                                │               └───────┬───────┘
                                │                       │
                                ▼                       ▼
                        ┌───────────────┐       ┌───────────────┐
                        │    FAISS      │       │    OpenAI     │
                        │  Vector Store │       │    LLM API    │
                        └───────────────┘       └───────────────┘
                                ▲
                                │
                        ┌───────────────┐
                        │  Ingestion    │
                        │  Pipeline     │
                        └───────────────┘
                                ▲
                                │
                        ┌───────────────┐
                        │  PDF Files    │
                        │  ./data/pdfs  │
                        └───────────────┘
```

## 🚀 Features

- **LangGraph Server**: Production-ready agent server with built-in streaming support
- **Agent Chat UI**: Official LangChain chat interface with thread management
- **Document Ingestion**: Parse PDFs, chunk text, and embed into FAISS vector store
- **Incremental Updates**: Only re-indexes documents that have changed (SHA256 hash tracking)
- **Tool-Using Agent**: Agent with `search_documents` tool for knowledge base queries
- **Streaming Responses**: Real-time token streaming via LangGraph Server protocol
- **Citations**: Returns source documents with file names and page numbers
- **Production Ready**: Docker, linting, testing, type checking

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

### 2. Add PDF Documents

```bash
# Add your PDF files to data/docs/ or data/pdfs/
cp your-documents.pdf data/docs/
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

### 4. Ingest Documents

```bash
# Via CLI inside the container
docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs

# Check ingestion status
docker compose exec langgraph-server python -m src.ingestion.ingest --status
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

# Run ingestion
python -m src.ingestion.ingest --pdf-dir ../data/pdfs

# Start LangGraph development server
langgraph dev
```

The LangGraph Server will be available at http://localhost:2024

### UI Setup (Agent Chat UI)

```bash
cd ui

# Option 1: Use npx to create Agent Chat UI
npx create-agent-chat-app@latest .

# Option 2: Clone official repository
git clone https://github.com/langchain-ai/agent-chat-ui.git .

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if needed

# Start development server
npm run dev
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
├── .env.example             # Environment variables template
├── docker-compose.yml       # Docker orchestration
├── Makefile                 # Common commands
├── data/
│   └── pdfs/                # Place your PDF files here
│
├── backend/
│   ├── pyproject.toml       # Python dependencies & config
│   ├── langgraph.json       # LangGraph Server configuration
│   ├── Dockerfile           # Backend container
│   └── src/
│       ├── agent/
│       │   ├── __init__.py
│       │   └── graph.py     # LangGraph agent with tools
│       ├── ingestion/
│       │   ├── ingest.py    # Main ingestion orchestrator
│       │   ├── loaders.py   # PDF document loaders (LlamaIndex)
│       │   ├── chunking.py  # Text chunking (LangChain)
│       │   ├── embeddings.py# OpenAI embeddings
│       │   ├── vectorstore.py# FAISS operations
│       │   └── manifest.py  # Document tracking manifest
│       └── config.py        # Configuration management
│
└── ui/
    ├── README.md            # UI setup instructions
    ├── .env.example         # UI environment template
    └── Dockerfile           # UI container (for Agent Chat UI)
```

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

# Run ingestion
docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs

# Access container shell
docker compose exec langgraph-server /bin/bash
```

## 🔒 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | Chat model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `FAISS_INDEX_PATH` | FAISS index directory | `./storage/faiss` |
| `MANIFEST_PATH` | Manifest file path | `./storage/manifest.json` |
| `PDF_DIR` | PDF documents directory | `./data/pdfs` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |
| `TOP_K` | Number of documents to retrieve | `5` |
| `LOG_LEVEL` | Logging level | `INFO` |

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

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) - LLM application framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent orchestration
- [Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) - Official chat interface
- [LlamaIndex](https://www.llamaindex.ai/) - Document parsing
- [FAISS](https://github.com/facebookresearch/faiss) - Vector search
- [OpenAI](https://openai.com/) - LLM provider
