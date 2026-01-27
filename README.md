# RAG AI Agent Monorepo

A production-ready Retrieval-Augmented Generation (RAG) AI Agent built with **LangGraph Server**, **LangChain**, **LlamaIndex**, **FAISS**, and **OpenAI**. Features official **Agent Chat UI** with comprehensive analytics and monitoring.

**Build your own AI agent with custom knowledge base** - Production-ready solution for deploying conversational AI applications with document retrieval capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

## 📸 Screenshots

### 💬 AI Chat Interface - Real-time Streaming Responses

![chrome-capture-2026-01-27](https://github.com/user-attachments/assets/66d22e77-f575-4304-bce4-7c22b1d9740a)

### 📊 Analytics Dashboard - Performance Monitoring with Grafana

<img width="1467" height="785" alt="image" src="https://github.com/user-attachments/assets/9580097d-91c5-4867-a317-1478b8ce25c4" />

## 🎥 Live Demo

**[Try it now: AVideo AI Agent](https://avideoagent.ypt.me/)** - A fully functional AI assistant specialized in the [AVideo Platform](https://github.com/WWBN/AVideo) documentation, demonstrating enterprise-grade RAG capabilities with 500+ documents indexed.

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

## � How It Works

**Document Ingestion Pipeline:**
1. PDF/Markdown → Extract text → Chunk into segments → Generate embeddings → Store in FAISS
2. SHA256 hash tracking enables incremental updates (only changed files are re-processed)

**RAG Agent Flow:**
1. User question → LangGraph routes to agent → Agent uses `search_documents` tool
2. FAISS similarity search → Retrieve relevant chunks → LLM generates answer with citations
3. Response streams back to UI in real-time

## 📋 Prerequisites

- **Docker & Docker Compose** (handles all dependencies)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

## 🛠️ Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/YPT-ME/AIAgent/
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

For detailed development setup, testing, and contribution guidelines, see:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflows
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical deep dive

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

## 🔌 API Reference

LangGraph Server provides RESTful endpoints for thread management, streaming responses, and health checks.

📚 [Full API Documentation](https://langchain-ai.github.io/langgraph/cloud/quick_start/)



## 🐳 Useful Commands

```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Stop all services
docker compose down
```

## 📊 Analytics & Monitoring

Built-in real-time analytics with **ClickHouse + Grafana**:

- 📈 Response times, token usage, tool calls
- 👥 User engagement and session tracking  
- 🚨 Error monitoring and alerting
- ⚡ Handles millions of events/second

**Access Dashboard:** http://localhost:3002 (admin/admin)

📚 [Detailed Analytics Guide](backend/src/analytics/README.md)

## ⚙️ Configuration

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `LANGGRAPH_API_KEY` - Server authentication (min 32 chars)

**Optional:** Customize models, chunk sizes, rate limits, analytics settings, and more.

📋 [Complete Environment Variables Reference](.env.example)

## 🏗️ Architecture

See detailed system architecture, scalability considerations, and design decisions:

📚 [ARCHITECTURE.md](ARCHITECTURE.md)

##  Technology Stack

**Backend:** LangGraph, LangChain, LlamaIndex, FAISS, OpenAI, Python 3.11+  
**Frontend:** Next.js, TypeScript, Agent Chat UI  
**Analytics:** ClickHouse, Grafana  
**Infrastructure:** Docker, Docker Compose

## 🤝 Contributing

**Want to contribute?** Read [CONTRIBUTING.md](CONTRIBUTING.md) • [Code of Conduct](SECURITY.md)

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

**Built with ❤️ as a production-ready foundation for building custom AI agents**
