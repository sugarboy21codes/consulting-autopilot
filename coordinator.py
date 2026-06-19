"""
Coordinator module for the Consulting Autopilot.

Python acts as the coordinator, running three sequential Agent SDK queries:
1. Researcher - gathers company intelligence
2. Analyst - maps competitive landscape
3. Writer - synthesizes everything into a diagnostic brief

Each query runs as an independent Claude agent with its own system prompt
and tool restrictions. Results flow from one to the next via Python.

Enhancements:
  - Custom MCP server (king-makers-db) for past diagnostic lookups
  - Observability hooks logging every tool call to audit_log.jsonl
"""

import anyio
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

from prompts import RESEARCHER_PROMPT, ANALYST_PROMPT, WRITER_PROMPT
from tools import past_diagnostics_server
from hooks import tool_use_hooks


async def run_agent(
    prompt: str,
    system_prompt: str,
    allowed_tools: list[str],
    label: str,
    include_mcp: bool = False,
) -> str:
    """
    Run a single Agent SDK query and collect the text response.

    Args:
        prompt: The task-specific instruction for this agent.
        system_prompt: The agent's persona and methodology.
        allowed_tools: Which tools this agent can use (principle of least privilege).
        label: Human-readable name for logging.
        include_mcp: Whether to attach the King Makers MCP server.

    Returns:
        The agent's full text response as a string.
    """
    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"{'='*60}\n")

    # Build options with hooks (always) and MCP server (conditional)
    options_kwargs = {
        "system_prompt": system_prompt,
        "allowed_tools": allowed_tools,
        "max_turns": 15,
        "hooks": tool_use_hooks,
    }

    # Attach MCP server only to agents that need it
    if include_mcp:
        options_kwargs["mcp_servers"] = {
            "king-makers-db": past_diagnostics_server,
        }
        # Add MCP tool names to allowed tools
        options_kwargs["allowed_tools"] = allowed_tools + [
            "mcp__king-makers-db__check_past_diagnostics",
            "mcp__king-makers-db__register_diagnostic",
        ]

    options = ClaudeAgentOptions(**options_kwargs)

    collected_text = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    collected_text.append(block.text)
                    print(".", end="", flush=True)

    result = "\n".join(collected_text)
    print(f"\n\n  {label} complete. ({len(result)} characters)")
    return result


async def run_diagnostic(company_url: str, problem_statement: str, output_dir: str = "output") -> str:
    """
    Run the full diagnostic pipeline: research -> analyze -> write.

    Args:
        company_url: The target company's website URL.
        problem_statement: What the client says their challenge is.
        output_dir: Directory to save the final brief.

    Returns:
        Path to the generated diagnostic brief.
    """
    print("\n" + "#"*60)
    print("  KING MAKERS CONSULTING AUTOPILOT")
    print("  Diagnostic Brief Generator")
    print("#"*60)
    print(f"\n  Target:  {company_url}")
    print(f"  Problem: {problem_statement}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ---------------------------------------------------------------
    # STEP 1: Research the company
    # The researcher gets the MCP server so it can check for
    # previous diagnostics before starting fresh research.
    # ---------------------------------------------------------------
    researcher_prompt = f"""Research the following company thoroughly.

Company URL: {company_url}

The client has described their challenge as: "{problem_statement}"

FIRST, use the check_past_diagnostics tool to see if King Makers has
analyzed this company before. If a previous diagnostic exists, review
it and focus your research on what has changed since then.

THEN, use your web tools to research the company. Start by fetching
their website, then run targeted searches. Focus on areas most
relevant to their stated problem.

Return your findings in the structured format specified in your instructions."""

    research_findings = await run_agent(
        prompt=researcher_prompt,
        system_prompt=RESEARCHER_PROMPT,
        allowed_tools=["WebSearch", "WebFetch"],
        label="Company Researcher",
        include_mcp=True,
    )

    # ---------------------------------------------------------------
    # STEP 2: Analyze the industry
    # ---------------------------------------------------------------
    analyst_prompt = f"""Analyze the competitive landscape and industry context for the following company.

Company URL: {company_url}

Here is what our researcher found about the company:

---
{research_findings}
---

The client's stated challenge is: "{problem_statement}"

Based on the researcher's findings, identify the industry this company
operates in, map 3-5 competitors, and analyze macro trends.
Return your findings in the structured format specified in your instructions."""

    industry_analysis = await run_agent(
        prompt=analyst_prompt,
        system_prompt=ANALYST_PROMPT,
        allowed_tools=["WebSearch", "WebFetch"],
        label="Industry Analyst",
    )

    # ---------------------------------------------------------------
    # STEP 3: Write the diagnostic brief
    # ---------------------------------------------------------------
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    company_slug = company_url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    brief_filename = f"diagnostic_brief_{company_slug}_{timestamp}.md"
    brief_path = output_path / brief_filename

    writer_prompt = f"""Write a diagnostic brief for the following engagement.

Company URL: {company_url}
Client's stated challenge: "{problem_statement}"

## Research findings from our researcher:

{research_findings}

## Industry analysis from our analyst:

{industry_analysis}

---

Synthesize all of the above into a polished diagnostic brief following
the exact document structure in your instructions.

Save the completed brief as a markdown file at: {brief_path}

Today's date is {datetime.now().strftime('%B %d, %Y')}."""

    writer_output = await run_agent(
        prompt=writer_prompt,
        system_prompt=WRITER_PROMPT,
        allowed_tools=["Read", "Write"],
        label="Diagnostic Writer",
    )

    # ---------------------------------------------------------------
    # STEP 4: Register the completed diagnostic
    # This step uses a separate agent call to log the engagement
    # in the King Makers registry via the MCP tool.
    # ---------------------------------------------------------------
    company_name = company_url.replace("https://", "").replace("http://", "").split("/")[0]

    register_prompt = f"""Register this completed diagnostic in King Makers' internal registry.

Use the register_diagnostic tool with these details:
- company_name: "{company_name}"
- company_url: "{company_url}"
- brief_path: "{brief_path}"
- problem_statement: "{problem_statement}"
"""

    await run_agent(
        prompt=register_prompt,
        system_prompt="You are a system assistant. Use the register_diagnostic tool to log the completed engagement.",
        allowed_tools=[],
        label="Registry Update",
        include_mcp=True,
    )

    # ---------------------------------------------------------------
    # STEP 5: Verify the output exists
    # ---------------------------------------------------------------
    if brief_path.exists():
        print(f"\n{'#'*60}")
        print(f"  DIAGNOSTIC BRIEF GENERATED SUCCESSFULLY")
        print(f"  Location: {brief_path}")
        print(f"  Size: {brief_path.stat().st_size:,} bytes")
        print(f"  Audit log: output/audit_log.jsonl")
        print(f"{'#'*60}\n")
        return str(brief_path)
    else:
        md_files = sorted(output_path.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if md_files:
            actual_path = md_files[0]
            print(f"\n  Brief found at: {actual_path}")
            return str(actual_path)
        else:
            print("\n  Writer did not save a file. Saving output directly...")
            brief_path.write_text(writer_output)
            print(f"  Saved to: {brief_path}")
            return str(brief_path)