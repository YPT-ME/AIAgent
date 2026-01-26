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
"""

import logging
import os
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
    
    prompt_file = Path(__file__).parent / "system_prompt.txt"
    
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
    """Minimal fallback prompt if file loading fails."""
    return """You are a helpful assistant for AVideo Platform.
    
Answer questions about AVideo Platform using the available documentation.
Always cite sources and provide accurate information.
For complex issues, recommend contacting support at https://streamphp.com/marketplace/
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
    
    vectorstore = get_or_create_vectorstore()
    
    if vectorstore is None:
        return "The knowledge base is not available. Please ensure documents have been ingested first using the rag-ingest command."
    
    try:
        # Perform similarity search with scores
        results = vectorstore.similarity_search_with_score(query=query, k=TOP_K)
        
        if not results:
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
            source_ref += f"\nRelevance: {1 - score:.2f}"
            
            formatted_results.append(f"{source_ref}\n\nContent:\n{doc.page_content}\n")
        
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"An error occurred while searching: {str(e)}"


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


def call_model(state: MessagesState) -> dict[str, Any]:
    """
    Call the LLM model with the current messages.
    
    Args:
        state: Current message state with conversation history
        
    Returns:
        Updated state with AI response
    """
    messages = state["messages"]
    
    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=RAG_SYSTEM_PROMPT)] + list(messages)
    
    # Call the model
    response = llm.invoke(messages)
    
    return {"messages": [response]}


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
