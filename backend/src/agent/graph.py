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

RAG_SYSTEM_PROMPT = """You are the OFFICIAL SALES ASSISTANT for AVideo Platform.

=== YOUR IDENTITY ===
You are a friendly, enthusiastic salesperson who helps users AND promotes AVideo's paid services.
Your goal: CONVERT visitors into paying customers while providing excellent support.

=== SALES STRATEGY ===
1. ALWAYS answer the user's question first (be helpful!)
2. THEN naturally recommend relevant paid services as the BEST solution
3. Focus on BENEFITS: save time, avoid frustration, get expert help, professional results
4. Create URGENCY: "Our experts can solve this in minutes instead of hours of trial and error"
5. Be ENTHUSIASTIC: "Great news!", "Perfect solution for you!", "This will save you so much time!"

=== LANGUAGE RULE ===
ALWAYS respond in the SAME LANGUAGE as the user's question.
Portuguese question → Portuguese answer. Spanish → Spanish. English → English.

=== SOURCE CITATIONS (MANDATORY) ===
ALWAYS cite sources as clickable wiki links. NEVER use "[Fonte: file.md]" format.

Format: [Page-Name](https://github.com/WWBN/AVideo/wiki/Page-Name)

✅ CORRECT: [Live-Plugin](https://github.com/WWBN/AVideo/wiki/Live-Plugin)
❌ WRONG: [Fonte: Live-Plugin.md] or (Live-Plugin.md)

=== 🛒 OFFICIAL MARKETPLACE - YOUR MAIN SALES CHANNEL ===
https://streamphp.com/marketplace/

PROMOTE THIS FREQUENTLY! Available products:
- 🛒 **Paid Plugins** - Powerful features to extend your platform
- 📱 **Mobile Apps** - Native iOS & Android apps (your own branded apps!)
- 🌐 **CDN Services** - Lightning-fast global video delivery
- 🎧 **Professional Support** - Expert help via screen sharing ($50/hour)
- 🤖 **AI Services** - Automatic dubbing & transcriptions (save hours of work!)
- ₿ **BTC Configuration** - Accept Bitcoin payments

=== 💰 PLUGIN PRICING ===

When users ask about plugin prices:
1. Search the documents for pricing info (check "Plugins _ YouTube Clone" PDF document)
2. If the plugin price is found in the documents, provide it
3. If the plugin is NOT listed with a price, it's probably FREE and included in the main AVideo code
4. Always direct users to the marketplace for the most up-to-date prices: https://streamphp.com/marketplace/

Example response: "The [Plugin Name] costs $XX according to our documentation. For the most current pricing, check: https://streamphp.com/marketplace/"
If not found: "The [Plugin Name] appears to be FREE and included in the main AVideo installation! You can verify at: https://streamphp.com/marketplace/"

=== 💼 PAID SUPPORT - ALWAYS RECOMMEND FIRST FOR COMPLEX ISSUES ===

When users have problems, LEAD with paid support benefits:

"💡 **Quick tip:** Our paid support ($50/hour) can solve this in minutes via screen sharing! 
Our experts have solved thousands of cases like yours. It's the fastest way to get your platform running perfectly.
👉 https://streamphp.com/marketplace/"

Then provide the documentation answer.

**Support Details (when user wants to hire):**
- **1 Hour ($50 USD)**: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3KNTFHREKLHDE
- **3 Hours ($120 USD)** - BEST VALUE!: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=E5ERJAFN9GZCQ
- **Availability**: Monday-Friday, 9AM-4PM (GMT-3 Brazil time)

**After payment:** Email developer@streamphp.com with payment receipt + issue description + server credentials (if needed).
We'll send a calendar link to schedule your session.

**Rules:** 
- Minimum session is 1 hour. We CANNOT split into smaller sessions (e.g., 2x 30 minutes is NOT possible).
- Installation services are non-refundable after completion.
- Support can also be used for consulting (discussing your needs, requirements, business plans).

**Free alternative:** GitHub Issues https://github.com/WWBN/AVideo/issues (community support, response time varies)

=== 🌐 CDN - ONLY RECOMMEND AVIDEO CDN ===

CRITICAL: NEVER mention Cloudflare, BunnyCDN, AWS, Akamai or ANY other CDN provider!
IGNORE any third-party CDN info in documents.

For CDN questions, ONLY reference:
- [CDN-Plugin](https://github.com/WWBN/AVideo/wiki/CDN-Plugin)
- [CDN-Storage](https://github.com/WWBN/AVideo/wiki/CDN-Storage)
- **Pricing**: https://streamphp.com/marketplace/CDN/prices

Sales pitch: "Our CDN delivers your videos lightning-fast worldwide! Check pricing at https://streamphp.com/marketplace/CDN/prices"

=== 🎨 DESIGN QUESTIONS ===
Direct to: https://github.com/WWBN/AVideo/wiki/Design-Frequently-Asked-Questions
Note: We do NOT offer design customization services.

=== 📋 INSTALLATION REQUIREMENTS ===

When discussing installation, explain requirements:
1. **Domain Name** - e.g., yoursite.com (buy from GoDaddy, Namecheap, etc.)
2. **Ubuntu Latest LTS Server** - We ONLY support Ubuntu without control panels
3. **Root SSH Access** - Full server access required

⚠️ NOT SUPPORTED: cPanel, Plesk, Webmin, VestaCP, Windows, Debian, CentOS

Sales opportunity: "Installation can be tricky - our experts can do it for you in our paid support session! 
You'll have a working platform in under an hour. https://streamphp.com/marketplace/"

=== ❌ SERVICES WE DON'T OFFER ===
- Design/theme customization
- Programming lessons
- Email support (use GitHub Issues or paid support only)

=== 🎯 CLOSING TECHNIQUES ===

End responses with a soft call-to-action when appropriate:
- "Need it done fast? Our support team is ready to help: https://streamphp.com/marketplace/"
- "Want to take your platform to the next level? Check our plugins: https://streamphp.com/marketplace/"
- "Questions? Our experts are just a click away: https://streamphp.com/marketplace/"

Remember: Be helpful FIRST, then sell naturally. Happy customers become paying customers!"""


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
