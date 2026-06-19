"""
Coordinator module for the Consulting Autopilot.

Python acts as the coordinator, running three sequential Agent SDK queries:
1. Researcher - gathers company intelligence
2. Analyst - maps competitive landscape
3. Writer - synthesizes everything into a diagnostic brief

Each query runs as an independent Claude agent with its own system prompt
and tool restrictions. Results flow from one to the next via Python.
"""

import anyio
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


from prompts import RESEARCHER_PROMPT, ANALYST_PROMPT, WRITER_PROMPT


async def run_agent(
    prompt: str,
    system_prompt: str,
    allowed_tools: list[str],
    label: str,
) -> str:
    """
    Run a single Agent SDK query and collect the text response.

    Args:
        prompt: The task-specific instruction for this agent.
        system_prompt: The agent's persona and methodology.
        allowed_tools: Which tools this agent can use (principle of least privilege).
        label: Human-readable name for logging.

    Returns:
        The agent's full text response as a string.
    """
    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"{'='*60}\n")

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        max_turns=15,  # Safety limit: stop after 15 tool-use cycles
    )

    collected_text = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    collected_text.append(block.text)
                    # Print a progress dot for each text block received
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
    # ---------------------------------------------------------------
    researcher_prompt = f"""Research the following company thoroughly.

Company URL: {company_url}

The client has described their challenge as: "{problem_statement}"

Use this context to focus your research on areas most relevant to their 
stated problem. Start by fetching their website, then run targeted searches.

Return your findings in the structured format specified in your instructions."""

    research_findings = await run_agent(
        prompt=researcher_prompt,
        system_prompt=RESEARCHER_PROMPT,
        allowed_tools=["WebSearch", "WebFetch"],
        label="Company Researcher",
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
    # Ensure the output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate a filename based on the company URL
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
    # STEP 4: Verify the output exists
    # ---------------------------------------------------------------
    if brief_path.exists():
        print(f"\n{'#'*60}")
        print(f"  DIAGNOSTIC BRIEF GENERATED SUCCESSFULLY")
        print(f"  Location: {brief_path}")
        print(f"  Size: {brief_path.stat().st_size:,} bytes")
        print(f"{'#'*60}\n")
        return str(brief_path)
    else:
        # The writer may have saved to a slightly different path
        # Check if any new .md files exist in the output directory
        md_files = sorted(output_path.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if md_files:
            actual_path = md_files[0]
            print(f"\n  Brief found at: {actual_path}")
            return str(actual_path)
        else:
            # Fallback: save the writer's text output directly
            print("\n  Writer did not save a file. Saving output directly...")
            brief_path.write_text(writer_output)
            print(f"  Saved to: {brief_path}")
            return str(brief_path)
