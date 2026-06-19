"""
Custom MCP Server: Past Diagnostics Database

An in-process MCP server that gives Claude access to King Makers'
internal diagnostic history. This demonstrates custom MCP tool development with the Claude Agent SDK,
including the @tool decorator, create_sdk_mcp_server, tool annotations,
and enterprise integration patterns.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations


# ---------------------------------------------------------------------------
# Tool 1: Check for past diagnostics about a company
# ---------------------------------------------------------------------------

@tool(
    "check_past_diagnostics",
    "Search King Makers' internal database for any previous diagnostic briefs "
    "about a company. Returns the content of past briefs if found, or confirms "
    "no prior analysis exists. Use this BEFORE starting web research to avoid "
    "duplicating work and to build on prior findings.",
    {"company_name": str},
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def check_past_diagnostics(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search the output/ directory for any previous diagnostic briefs
    matching the company name. In production, this would query Supabase.
    """
    company_name = args["company_name"].lower().strip()
    output_dir = Path("output")

    if not output_dir.exists():
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "found": False,
                        "message": "No diagnostic history available. This is the first analysis.",
                        "company_searched": company_name,
                    }),
                }
            ]
        }

    # Search for briefs containing the company name in filename or content
    matching_briefs = []

    for brief_file in output_dir.glob("*.md"):
        # Check filename match
        if company_name.replace(" ", "") in brief_file.name.lower().replace(" ", ""):
            content = brief_file.read_text(encoding="utf-8")
            matching_briefs.append({
                "filename": brief_file.name,
                "created": datetime.fromtimestamp(
                    brief_file.stat().st_mtime
                ).isoformat(),
                "size_bytes": brief_file.stat().st_size,
                "content_preview": content[:2000],
            })
            continue

        # Check content match (company name appears in the brief)
        try:
            content = brief_file.read_text(encoding="utf-8")
            if company_name in content.lower():
                matching_briefs.append({
                    "filename": brief_file.name,
                    "created": datetime.fromtimestamp(
                        brief_file.stat().st_mtime
                    ).isoformat(),
                    "size_bytes": brief_file.stat().st_size,
                    "content_preview": content[:2000],
                })
        except (UnicodeDecodeError, PermissionError):
            continue

    if matching_briefs:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "found": True,
                        "count": len(matching_briefs),
                        "message": f"Found {len(matching_briefs)} previous diagnostic(s) for '{company_name}'.",
                        "briefs": matching_briefs,
                    }),
                }
            ]
        }

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "found": False,
                    "message": f"No previous diagnostics found for '{company_name}'. This will be the first analysis.",
                    "company_searched": company_name,
                }),
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tool 2: Log a completed diagnostic to the registry
# ---------------------------------------------------------------------------

@tool(
    "register_diagnostic",
    "Register a completed diagnostic brief in King Makers' internal registry. "
    "Call this after a diagnostic brief has been successfully written to record "
    "the engagement for future reference.",
    {
        "company_name": str,
        "company_url": str,
        "brief_path": str,
        "problem_statement": str,
    },
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False),
)
async def register_diagnostic(args: dict[str, Any]) -> dict[str, Any]:
    """
    Append a record to the diagnostics registry (JSON file).
    In production, this would write to Supabase.
    """
    registry_path = Path("output/registry.json")

    # Load existing registry or create new
    registry = []
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            registry = []

    # Add new entry
    entry = {
        "company_name": args["company_name"],
        "company_url": args["company_url"],
        "brief_path": args["brief_path"],
        "problem_statement": args["problem_statement"],
        "completed_at": datetime.now().isoformat(),
    }
    registry.append(entry)

    # Save registry
    registry_path.write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "registered": True,
                    "entry": entry,
                    "total_diagnostics": len(registry),
                }),
            }
        ]
    }


# ---------------------------------------------------------------------------
# Bundle tools into an MCP server
# ---------------------------------------------------------------------------

past_diagnostics_server = create_sdk_mcp_server(
    name="king-makers-db",
    version="1.0.0",
    tools=[check_past_diagnostics, register_diagnostic],
)