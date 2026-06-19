#!/usr/bin/env python3
"""
King Makers Consulting Autopilot
================================
CLI tool that generates diagnostic briefs for prospective consulting clients.

Usage:
    python main.py <company_url> "<problem_statement>"

Example:
    python main.py https://acmewidgets.com "struggling with employee retention in warehouse operations"

Environment:
    ANTHROPIC_API_KEY must be set (same key you use for other Anthropic projects).
"""

import sys
import os
import anyio

from coordinator import run_diagnostic


def print_usage():
    print("""
    King Makers Consulting Autopilot
    ================================
    
    Usage:
        python main.py <company_url> "<problem_statement>"
    
    Arguments:
        company_url       The target company's website (e.g., https://example.com)
        problem_statement The client's stated challenge (wrap in quotes)
    
    Example:
        python main.py https://acmewidgets.com "struggling with employee retention"
    
    Environment:
        Set ANTHROPIC_API_KEY before running.
    """)


def validate_inputs(url: str, problem: str) -> tuple[str, str]:
    """Validate and clean inputs before running the agent pipeline."""
    # Ensure URL has a scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Ensure problem statement is non-empty
    if len(problem.strip()) < 10:
        print("Error: Problem statement is too short. Provide at least a sentence.")
        sys.exit(1)

    return url, problem.strip()


async def main():
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    # Parse arguments
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    company_url = sys.argv[1]
    problem_statement = sys.argv[2]

    # Validate
    company_url, problem_statement = validate_inputs(company_url, problem_statement)

    # Run the diagnostic pipeline
    try:
        brief_path = await run_diagnostic(
            company_url=company_url,
            problem_statement=problem_statement,
            output_dir="output",
        )

        print(f"\nDone. Open your brief at:\n  {brief_path}\n")

    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError during diagnostic generation: {e}")
        print("Check your API key and network connection, then try again.")
        sys.exit(1)


if __name__ == "__main__":
    anyio.run(main)
