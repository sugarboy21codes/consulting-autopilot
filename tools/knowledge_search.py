"""
Custom MCP Tool: Knowledge Base Search

An in-process MCP tool that gives Claude access to King Makers'
vector-embedded knowledge base. The analyst agent uses this to
retrieve relevant institutional knowledge before doing web research.
"""

import json
from typing import Any
from pathlib import Path

from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

from rag import KingMakersKnowledgeBase


# ---------------------------------------------------------------------------
# Initialize the knowledge base (singleton)
# ---------------------------------------------------------------------------

_kb = KingMakersKnowledgeBase(persist_dir=".chromadb")


def get_knowledge_base() -> KingMakersKnowledgeBase:
    """Access the shared knowledge base instance."""
    return _kb


# ---------------------------------------------------------------------------
# Tool 1: Search the knowledge base
# ---------------------------------------------------------------------------

@tool(
    "search_knowledge_base",
    "Search King Makers' internal knowledge base for insights from past "
    "consulting engagements. This contains embedded chunks from previous "
    "diagnostic briefs, industry analyses, and institutional knowledge. "
    "Use this to find patterns, frameworks, and insights that King Makers "
    "has developed through prior work. Returns the most relevant text "
    "chunks with source attribution.",
    {
        "query": str,
        "max_results": int,
    },
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def search_knowledge_base(args: dict[str, Any]) -> dict[str, Any]:
    """
    Query the ChromaDB vector store for relevant knowledge chunks.
    """
    query_text = args["query"]
    max_results = min(args.get("max_results", 5), 10)

    kb = get_knowledge_base()
    results = kb.query(query_text=query_text, n_results=max_results)

    if not results:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "found": False,
                        "message": "No relevant knowledge found. The knowledge base may be empty or the query did not match any stored content.",
                        "query": query_text,
                        "knowledge_base_stats": kb.get_stats(),
                    }),
                }
            ]
        }

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "found": True,
                    "count": len(results),
                    "query": query_text,
                    "results": results,
                    "knowledge_base_stats": kb.get_stats(),
                }),
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tool 2: Get knowledge base stats
# ---------------------------------------------------------------------------

@tool(
    "knowledge_base_stats",
    "Get statistics about King Makers' knowledge base, including how many "
    "document chunks are stored and what sources have been ingested.",
    {},
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def knowledge_base_stats(args: dict[str, Any]) -> dict[str, Any]:
    """
    Return current knowledge base statistics.
    """
    kb = get_knowledge_base()
    stats = kb.get_stats()

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(stats),
            }
        ]
    }


# ---------------------------------------------------------------------------
# Bundle into MCP server
# ---------------------------------------------------------------------------

knowledge_base_server = create_sdk_mcp_server(
    name="king-makers-rag",
    version="1.0.0",
    tools=[search_knowledge_base, knowledge_base_stats],
)