"""
Observability Hooks for the Consulting Autopilot

PreToolUse and PostToolUse hooks that log every tool call to a
structured JSON audit file. This demonstrates hook callbacks for agent observability, including
PreToolUse and PostToolUse event handling, structured audit logging,
and production governance patterns.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookMatcher


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AUDIT_LOG_PATH = Path("output/audit_log.jsonl")

# In-memory timing tracker to calculate tool execution duration
_tool_start_times: dict[str, float] = {}


# ---------------------------------------------------------------------------
# PreToolUse Hook: Log before each tool call
# ---------------------------------------------------------------------------

async def log_pre_tool_use(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """
    Fires before every tool execution. Logs what tool is being called,
    with what parameters, and starts a timer to measure duration.

    This hook allows all tool calls (no blocking). In a production
    system, you could add guardrails here to deny dangerous operations.
    """
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    # Start timing
    if tool_use_id:
        _tool_start_times[tool_use_id] = time.time()

    # Build the audit entry
    audit_entry = {
        "event": "pre_tool_use",
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_use_id": tool_use_id,
        "input_summary": _summarize_input(tool_input),
    }

    # Append to audit log (JSONL format: one JSON object per line)
    _write_audit_entry(audit_entry)

    # Print to console for real-time visibility
    print(f"  [HOOK] Pre  | {tool_name} | id={tool_use_id}")

    # Return empty dict = allow the tool call to proceed
    return {}


# ---------------------------------------------------------------------------
# PostToolUse Hook: Log after each tool call
# ---------------------------------------------------------------------------

async def log_post_tool_use(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """
    Fires after every tool execution. Logs the result status and
    calculates how long the tool call took.
    """
    tool_name = input_data.get("tool_name", "unknown")

    # Calculate duration
    duration_ms = None
    if tool_use_id and tool_use_id in _tool_start_times:
        duration_ms = round(
            (time.time() - _tool_start_times.pop(tool_use_id)) * 1000
        )

    # Build the audit entry
    audit_entry = {
        "event": "post_tool_use",
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_use_id": tool_use_id,
        "duration_ms": duration_ms,
    }

    _write_audit_entry(audit_entry)

    print(f"  [HOOK] Post | {tool_name} | {duration_ms}ms | id={tool_use_id}")

    return {}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _summarize_input(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Create a safe summary of tool input for logging.
    Truncates long values to prevent audit log bloat.
    """
    summary = {}
    for key, value in tool_input.items():
        if isinstance(value, str) and len(value) > 200:
            summary[key] = value[:200] + "...[truncated]"
        else:
            summary[key] = value
    return summary


def _write_audit_entry(entry: dict[str, Any]) -> None:
    """
    Append a single audit entry to the JSONL log file.
    Creates the file and parent directories if needed.
    """
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Export: Hook configuration ready to pass to ClaudeAgentOptions
# ---------------------------------------------------------------------------

tool_use_hooks = {
    "PreToolUse": [
        HookMatcher(matcher=None, hooks=[log_pre_tool_use]),
    ],
    "PostToolUse": [
        HookMatcher(matcher=None, hooks=[log_post_tool_use]),
    ],
}