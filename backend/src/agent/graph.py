"""
RAG AI Agent - LangGraph Server Compatible Agent

This module defines a LangGraph-based RAG agent that is fully compatible with
LangGraph Server and Agent Chat UI. It uses the standard message-based interface
that Agent Chat UI expects.

The agent:
1. Receives user messages via the standard LangGraph message format
2. Retrieves relevant documents from the FAISS vector store
3. Generates answers with citations using OpenAI
4. Streams responses back through LangGraph Server
5. Tracks analytics metrics for monitoring and optimization
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Any, Literal

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread pool for async analytics tracking
_analytics_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analytics")

# Analytics API configuration
ANALYTICS_API_URL = os.getenv("ANALYTICS_API_URL", "http://analytics-api:8080")


# =============================================================================
# Analytics Integration (via HTTP API)
# =============================================================================

def track_tool_call_http(thread_id: str, tool_name: str, duration_ms: int, success: bool, error_message: str = None):
    """Track tool call via HTTP API in background."""
    try:
        import httpx
        url = f"{ANALYTICS_API_URL}/analytics/track/tool"
        logger.info(f"🔵 Tracking tool to {url}: tool={tool_name}, success={success}")
        with httpx.Client(timeout=2.0) as client:
            response = client.post(
                url,
                json={
                    "thread_id": thread_id,
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "success": success,
                    "error_message": error_message
                }
            )
            logger.info(f"✅ Tool tracking successful: status={response.status_code}")
    except Exception as e:
        logger.error(f"❌ Failed to track tool call: {e}")


def track_message_http(thread_id: str, user_id: str, message_type: str, content: str, 
                       tokens: int, duration_ms: int, model: str):
    """Track message via HTTP API in background."""
    try:
        import httpx
        url = f"{ANALYTICS_API_URL}/analytics/track/message"
        logger.info(f"🔵 Tracking message to {url}: thread={thread_id}, type={message_type}")
        with httpx.Client(timeout=2.0) as client:
            response = client.post(
                url,
                json={
                    "thread_id": thread_id,
                    "user_id": user_id or "anonymous",
                    "message_type": message_type,
                    "content_length": len(content),
                    "tokens": tokens,
                    "duration_ms": duration_ms,
                    "model": model
                }
            )
            logger.info(f"✅ Tracking successful: status={response.status_code}")
    except Exception as e:
        logger.error(f"❌ Failed to track message: {e}")


# =============================================================================
# Configuration
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./storage/faiss")
TOP_K = int(os.getenv("TOP_K", "5"))


# =============================================================================
# RAG System Prompt
# =============================================================================

WIKI_BASE_URL = "https://github.com/WWBN/AVideo/wiki/"


def load_system_prompt() -> str:
    """
    Load the system prompt from external file.
    
    This allows easy maintenance and updates without touching Python code.
    Falls back to a minimal prompt if file cannot be loaded.
    
    Returns:
        The system prompt string
    """
    from pathlib import Path
    
    prompt_file = Path(__file__).parent.parent.parent / "system_prompt.txt"
    
    try:
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"System prompt loaded from {prompt_file}")
                return content
        else:
            logger.warning(f"System prompt file not found at {prompt_file}, using fallback")
            return _get_fallback_prompt()
    except Exception as e:
        logger.error(f"Failed to load system prompt: {e}, using fallback")
        return _get_fallback_prompt()


def _get_fallback_prompt() -> str:
    """
    Load fallback prompt from example file.
    
    Returns:
        Fallback prompt from system_prompt.example.txt or hardcoded default
    """
    from pathlib import Path
    
    example_file = Path(__file__).parent.parent.parent / "system_prompt.example.txt"
    
    try:
        if example_file.exists():
            with open(example_file, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Fallback prompt loaded from {example_file}")
                return content
        else:
            logger.warning(f"Example prompt file not found at {example_file}, using hardcoded fallback")
            return _get_hardcoded_fallback()
    except Exception as e:
        logger.error(f"Failed to load example prompt: {e}, using hardcoded fallback")
        return _get_hardcoded_fallback()


def _get_hardcoded_fallback() -> str:
    """Hardcoded fallback if even the example file cannot be loaded."""
    return """You are a helpful AI assistant with access to a knowledge base.

Answer questions based on the documentation available through the search_documents tool.
Always cite your sources and provide clear, accurate information.
If you cannot find relevant information, be honest about it.
"""


# Load the system prompt at module initialization
RAG_SYSTEM_PROMPT = load_system_prompt()


# =============================================================================
# Vector Store Initialization
# =============================================================================

def get_vectorstore():
    """
    Load or initialize the FAISS vector store.
    
    Returns:
        FAISS vectorstore or None if not available
    """
    from pathlib import Path
    
    try:
        from langchain_community.vectorstores import FAISS
        
        index_path = Path(FAISS_INDEX_PATH)
        
        if not index_path.exists() or not (index_path / "index.faiss").exists():
            logger.warning(f"FAISS index not found at {index_path}")
            return None
        
        embeddings = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )
        
        vectorstore = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        
        logger.info(f"FAISS vectorstore loaded from {index_path}")
        return vectorstore
        
    except Exception as e:
        logger.error(f"Failed to load FAISS vectorstore: {e}")
        return None


# Global vectorstore instance
_vectorstore = None


def get_or_create_vectorstore():
    """Get or create the global vectorstore instance."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


# =============================================================================
# Tools
# =============================================================================

@tool
def search_documents(query: str) -> str:
    """
    Search the knowledge base for documents relevant to the query.
    
    Use this tool to find information from the document knowledge base.
    Pass the user's question or key terms as the query.
    
    Args:
        query: The search query to find relevant documents
        
    Returns:
        A formatted string containing the relevant document excerpts with source citations
    """
    logger.info(f"Searching for: {query[:100]}...")
    
    # Track tool call start time
    start_time = time.time()
    success = False
    error_message = None
    
    try:
        vectorstore = get_or_create_vectorstore()
        
        if vectorstore is None:
            error_message = "Knowledge base not available"
            return "The knowledge base is not available. Please ensure documents have been ingested first using the rag-ingest command."
        
        # Perform similarity search with normalized relevance scores (0-1, higher = more relevant).
        # FAISS's raw similarity_search_with_score returns an unbounded L2 distance, which is
        # not directly usable as "1 - score" (that previously showed relevant docs as negative).
        results = vectorstore.similarity_search_with_relevance_scores(query=query, k=TOP_K)
        
        if not results:
            success = True
            return "No relevant documents found for your query."
        
        # Format results
        formatted_results = []
        
        for idx, (doc, score) in enumerate(results, 1):
            metadata = doc.metadata or {}
            file_name = metadata.get("file_name", "Unknown")
            page_number = metadata.get("page_number", None)
            file_type = metadata.get("file_type", "unknown")
            
            # Generate wiki URL from filename (remove .md extension)
            wiki_page = file_name.replace(".md", "").replace(".markdown", "")
            wiki_url = f"{WIKI_BASE_URL}{wiki_page}"
            
            source_ref = f"[Document {idx}: {file_name}"
            if page_number and file_type == "pdf":
                source_ref += f", Page {page_number}"
            source_ref += f"]\nWiki URL: {wiki_url}"
            source_ref += f"\nRelevance: {score:.2f}"
            
            formatted_results.append(f"{source_ref}\n\nContent:\n{doc.page_content}\n")
        
        success = True
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        error_message = str(e)
        return f"An error occurred while searching: {str(e)}"
    
    finally:
        # Track tool call metrics via HTTP API in background thread
        duration_ms = int((time.time() - start_time) * 1000)
        # Note: thread_id would ideally come from context, but LangGraph tools don't easily access it
        # For now using "unknown" - the analytics still track tool usage patterns
        thread_id = "unknown"
        _analytics_executor.submit(
            track_tool_call_http,
            thread_id,
            "search_documents",
            duration_ms,
            success,
            error_message
        )


# =============================================================================
# LangGraph Agent Definition
# =============================================================================

# Tools list
tools = [search_documents]

# Initialize the LLM with tools
llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    temperature=0.5,
    streaming=True,
).bind_tools(tools)


def should_continue(state: MessagesState) -> Literal["tools", END]:
    """
    Determine if the agent should continue to tools or end.
    
    Args:
        state: Current message state
        
    Returns:
        "tools" if there are tool calls, END otherwise
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If there are tool calls, route to tool node
    if last_message.tool_calls:
        return "tools"
    
    # Otherwise, end the conversation
    return END


def _extract_text_content(content) -> str:
    """
    Extract text from message content which can be string or list of content blocks.
    
    Args:
        content: Message content (string or list of dicts with 'type' and 'text')
        
    Returns:
        Plain text string
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Handle list of content blocks like [{'type': 'text', 'text': '...'}]
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif isinstance(item, str):
                texts.append(item)
        return ' '.join(texts)
    return str(content)


def call_model(state: MessagesState, config: dict = None) -> dict[str, Any]:
    """
    Call the LLM model with the current messages.
    
    Args:
        state: Current message state with conversation history
        config: Runtime configuration with thread_id, user_id, etc.
        
    Returns:
        Updated state with AI response
    """
    messages = state["messages"]
    
    # Extract config values early for logging
    config = config or {}
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "unknown")
    user_id = configurable.get("user_id", "anonymous")
    
    # Extract user IP from config (passed via LangGraph Server headers/metadata)
    user_ip = configurable.get("user_ip") or configurable.get("x_forwarded_for") or configurable.get("client_ip", "unknown")
    
    # Log the user's question (last human message)
    user_question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = _extract_text_content(msg.content)
            break
    
    if user_question:
        logger.info(f"📝 [QUESTION] thread_id={thread_id} | user_ip={user_ip} | user_id={user_id} | question={user_question}")
    
    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=RAG_SYSTEM_PROMPT)] + list(messages)
    
    # Track response start time
    start_time = time.time()
    
    try:
        # Call the model
        response = llm.invoke(messages)
        
        # Log the AI response
        response_content = _extract_text_content(response.content) if response.content else ""
        logger.info(f"🤖 [RESPONSE] thread_id={thread_id} | user_ip={user_ip} | response_length={len(response_content)} | response={response_content[:500]}{'...' if len(response_content) > 500 else ''}")
        
        # Track analytics for assistant response in background thread
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Count tokens (approximate)
        tokens = len(response_content) // 4 if response_content else 0
        
        _analytics_executor.submit(
            track_message_http,
            thread_id,
            user_id,
            "assistant",
            response_content,
            tokens,
            duration_ms,
            OPENAI_MODEL
        )
        
        return {"messages": [response]}
    
    except Exception as e:
        logger.error(f"Model call error: {e}")
        
        # Track error in background thread (simplified - no async complexity)
        logger.debug(f"Model call failed: {e}")
        
        raise


# Create the tool node
tool_node = ToolNode(tools)


# =============================================================================
# Build the Graph
# =============================================================================

def create_graph():
    """
    Create the LangGraph workflow for the RAG agent.
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the graph with MessagesState
    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )
    
    # Tools always return to agent
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    # Note: LangGraph Server handles persistence automatically.
    # No need to provide a custom checkpointer - it will be managed by the platform.
    return workflow.compile()


# Export the compiled graph for LangGraph Server
graph = create_graph()

logger.info("RAG Agent graph created and ready for LangGraph Server")
