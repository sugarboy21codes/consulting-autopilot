# King Makers Consulting Autopilot

An AI-powered diagnostic brief generator built with the Claude Agent SDK. Feed it a company URL and a problem statement, and it produces a structured consulting diagnostic ready for client conversations.

## What it does

The Consulting Autopilot runs a three-stage intelligence pipeline:

1. **Company Researcher** - Fetches the target company's website and runs targeted web searches to gather intelligence: leadership, recent news, funding, market positioning, and risk signals.

2. **Industry Analyst** - Maps the competitive landscape: identifies 3-5 competitors, analyzes macro trends, surfaces common industry pain points, and identifies white-space opportunities.

3. **Diagnostic Writer** - Synthesizes all research into a polished, client-ready diagnostic brief with executive summary, competitive assessment, key findings, 90-day quick wins, and strategic considerations.

Each stage runs as an independent Claude agent with restricted tool access (principle of least privilege). Python orchestrates the flow, passing results between stages.

## Architecture

```
Input: Company URL + Problem Statement
  |
  v
[Python Coordinator]
  |
  |--> Agent 1: Researcher (WebSearch, WebFetch)
  |         |
  |         v-- Company intelligence
  |
  |--> Agent 2: Analyst (WebSearch, WebFetch)  
  |         |
  |         v-- Industry analysis
  |
  |--> Agent 3: Writer (Read, Write)
  |         |
  |         v-- diagnostic_brief.md
  |
  v
Output: Structured consulting diagnostic
```

## Quick start

```bash
# Clone and set up
git clone https://github.com/sugarboy21codes/consulting-autopilot.git
cd consulting-autopilot
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Run a diagnostic
python main.py https://example.com "struggling with customer retention in their SaaS product"
```

The generated brief lands in the `output/` directory.

## Output format

The diagnostic brief follows a structured consulting format:

- **Executive summary** - 3-4 sentence synthesis of findings and core opportunity
- **Company snapshot** - Brief overview of the target company
- **The challenge in context** - Problem statement mapped against research findings
- **Competitive position assessment** - Where the company stands vs competitors
- **Key findings** - 3-5 evidence-backed insights with implications
- **Quick wins (90-day opportunities)** - Actionable short-term recommendations
- **Strategic considerations** - Longer-term questions to provoke thinking
- **Data limitations** - Intellectual honesty about what could not be verified

## Tech stack

- **Claude Agent SDK** (Python) - Autonomous agent orchestration
- **Claude Sonnet** - Powers each agent's reasoning
- **WebSearch / WebFetch** - Real-time company and industry research
- **Python 3.10+** - Coordinator logic and CLI

## Project structure

```
consulting-autopilot/
  main.py              # CLI entry point
  coordinator.py       # Python orchestrator for the three-agent pipeline
  prompts/
    coordinator.py     # Coordinator system prompt
    researcher.py      # Company researcher system prompt
    analyst.py         # Industry analyst system prompt
    writer.py          # Diagnostic writer system prompt
  output/              # Generated diagnostic briefs
  requirements.txt     # Dependencies
```

## Roadmap

- [ ] Phase 2: Expand diagnostic to full consulting proposal
- [ ] Phase 3: FastAPI backend for API access
- [ ] Phase 4: Next.js dashboard frontend
- [ ] Add equity research mode (TSX ticker analysis)
- [ ] Add job application research mode
- [ ] Add competitor intelligence monitoring mode

## Built by

[King Makers Inc](https://kingmakersinc.ca) - AI-native consulting and product company.

## License

MIT
