"""
Coordinator module for the Consulting Autopilot.

Python acts as the coordinator, running three sequential Agent SDK queries:
1. Researcher - gathers company intelligence (with past diagnostic lookup)
2. Analyst - maps competitive landscape (with RAG knowledge base)
3. Writer - synthesizes everything into a diagnostic brief

Each query runs as an independent Claude agent with its own system prompt
and tool restrictions. Results flow from one to the next via Python.

Capabilities:
  - Custom MCP servers for internal data access
  - Observability hooks logging every tool call
  - RAG knowledge base for institutional knowledge retrieval
"""

import anyio
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

from prompts import RESEARCHER_PROMPT, ANALYST_PROMPT, WRITER_PROMPT
from tools import past_diagnostics_server, knowledge_base_server, get_knowledge_base
from hooks import tool_use_hooks


def seed_knowledge_base(output_dir: str = "output") -> None:
    """
    Ingest any existing diagnostic briefs into the RAG knowledge base.
    This runs once at pipeline start to ensure the analyst has access
    to all prior institutional knowledge.
    """
    kb = get_knowledge_base()
    output_path = Path(output_dir)

    if not output_path.exists():
        print("  Knowledge base: no documents to ingest.")
        return

    results = kb.ingest_directory(output_path)
    stats = kb.get_stats()

    print(f"  Knowledge base: {results['files_processed']} new files ingested, "
          f"{results['files_skipped']} already indexed, "
          f"{stats['total_chunks']} total chunks stored.")


async def run_agent(
    prompt: str,
    system_prompt: str,
    allowed_tools: list[str],
    label: str,
    mcp_servers: dict | None = None,
    extra_allowed_tools: list[str] | None = None,
) -> str:
    """
    Run a single Agent SDK query and collect the text response.

    Args:
        prompt: The task-specific instruction for this agent.
        system_prompt: The agent's persona and methodology.
        allowed_tools: Which built-in tools this agent can use.
        label: Human-readable name for logging.
        mcp_servers: Optional dict of MCP servers to attach.
        extra_allowed_tools: Additional tool names to allow (MCP tools).

    Returns:
        The agent's full text response as a string.
    """
    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"{'='*60}\n")

    # Merge allowed tools
    all_allowed_tools = allowed_tools.copy()
    if extra_allowed_tools:
        all_allowed_tools.extend(extra_allowed_tools)

    # Build options
    options_kwargs = {
        "system_prompt": system_prompt,
        "allowed_tools": all_allowed_tools,
        "max_turns": 15,
        "hooks": tool_use_hooks,
    }

    if mcp_servers:
        options_kwargs["mcp_servers"] = mcp_servers

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
    # STEP 0: Seed the RAG knowledge base with existing briefs
    # ---------------------------------------------------------------
    print(f"\n  Initializing knowledge base...")
    seed_knowledge_base(output_dir)

    # ---------------------------------------------------------------
    # STEP 1: Research the company
    # The researcher gets the client DB MCP server so it can check
    # for previous diagnostics before starting fresh research.
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
        mcp_servers={
            "king-makers-db": past_diagnostics_server,
        },
        extra_allowed_tools=[
            "mcp__king-makers-db__check_past_diagnostics",
            "mcp__king-makers-db__register_diagnostic",
        ],
    )

    # ---------------------------------------------------------------
    # STEP 2: Analyze the industry
    # The analyst gets the RAG MCP server so it can retrieve
    # institutional knowledge from past engagements.
    # ---------------------------------------------------------------
    analyst_prompt = f"""Analyze the competitive landscape and industry context for the following company.

Company URL: {company_url}

Here is what our researcher found about the company:

---
{research_findings}
---

The client's stated challenge is: "{problem_statement}"

FIRST, use the search_knowledge_base tool to check if King Makers has
institutional knowledge about this industry or similar challenges from
past engagements. Search for the industry name and the type of challenge
described. This gives you a head start with patterns we have already identified.

THEN, use your web tools to research the industry. Identify 3-5
competitors, analyze macro trends, and map common pain points.

Combine insights from the knowledge base with fresh web research.
Return your findings in the structured format specified in your instructions."""

    industry_analysis = await run_agent(
        prompt=analyst_prompt,
        system_prompt=ANALYST_PROMPT,
        allowed_tools=["WebSearch", "WebFetch"],
        label="Industry Analyst",
        mcp_servers={
            "king-makers-rag": knowledge_base_server,
        },
        extra_allowed_tools=[
            "mcp__king-makers-rag__search_knowledge_base",
            "mcp__king-makers-rag__knowledge_base_stats",
        ],
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
    # ---------------------------------------------------------------
    company_name = company_url.replace("https://", "").replace("http://", "").split("/")[0]

    register_prompt = f"""Register this completed diagnostic in King Makers' internal registry.

Use the register_diagnostic tool with these details:
- company_name: "{company_name}"
- company_url: "{company_url}"
- brief_path: "{brief_path}"
- problem_statement: "{problem_statement}"
"""

    try:
        await run_agent(
            prompt=register_prompt,
            system_prompt="You are a system assistant. Use the register_diagnostic tool to log the completed engagement.",
            allowed_tools=[],
            label="Registry Update",
            mcp_servers={
                "king-makers-db": past_diagnostics_server,
            },
            extra_allowed_tools=[
                "mcp__king-makers-db__register_diagnostic",
            ],
        )
    except Exception as e:
        print(f"\n  Registry update skipped (non-critical): {e}")

    # ---------------------------------------------------------------
    # STEP 5: Verify the output exists
    # ---------------------------------------------------------------
    if brief_path.exists():
        kb = get_knowledge_base()
        stats = kb.get_stats()
        print(f"\n{'#'*60}")
        print(f"  DIAGNOSTIC BRIEF GENERATED SUCCESSFULLY")
        print(f"  Location: {brief_path}")
        print(f"  Size: {brief_path.stat().st_size:,} bytes")
        print(f"  Audit log: output/audit_log.jsonl")
        print(f"  Knowledge base: {stats['total_chunks']} chunks stored")
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