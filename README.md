# King Makers Consulting Autopilot

An AI-powered diagnostic brief generator built with the Claude Agent SDK. Feed it a company URL and a problem statement, and it produces a structured consulting diagnostic ready for client conversations.

## What it does

The Consulting Autopilot runs a multi-agent intelligence pipeline with custom MCP tools, observability hooks, and a RAG knowledge base:

1. **Knowledge Base Seeding** - Ingests past diagnostic briefs into a ChromaDB vector store, building institutional knowledge that improves with every engagement.

2. **Company Researcher** - Checks for prior diagnostics via a custom MCP tool, then fetches the target company's website and runs targeted web searches to gather intelligence: leadership, recent news, funding, market positioning, and risk signals.

3. **Industry Analyst** - Queries the RAG knowledge base for institutional patterns from past engagements, then maps the competitive landscape: identifies 3-5 competitors, analyzes macro trends, surfaces common industry pain points, and identifies white-space opportunities.

4. **Diagnostic Writer** - Synthesizes all research into a polished, client-ready diagnostic brief with executive summary, competitive assessment, key findings, 90-day quick wins, and strategic considerations.

5. **Registry Update** - Logs the completed engagement in King Makers' internal registry via MCP tool for future reference.

Every tool call across all agents is logged to a structured JSONL audit file via PreToolUse and PostToolUse hooks for full observability.

## Architecture

```
Input: Company URL + Problem Statement
  |
  v
[Python Coordinator]
  |
  |-- Step 0: Seed RAG knowledge base (ChromaDB)
  |
  |--> Agent 1: Researcher
  |     MCP Tools: check_past_diagnostics (king-makers-db)
  |     Built-in: WebSearch, WebFetch
  |     Hooks: PreToolUse, PostToolUse (audit logging)
  |
  |--> Agent 2: Analyst
  |     MCP Tools: search_knowledge_base (king-makers-rag)
  |     Built-in: WebSearch, WebFetch
  |     Hooks: PreToolUse, PostToolUse (audit logging)
  |
  |--> Agent 3: Writer
  |     Built-in: Read, Write
  |     Hooks: PreToolUse, PostToolUse (audit logging)
  |
  |--> Agent 4: Registry (register_diagnostic)
  |
  v
Output: diagnostic_brief.md + audit_log.jsonl + registry.json
```

## Key capabilities

### Custom MCP Servers

Two in-process MCP servers built with the `@tool` decorator and `create_sdk_mcp_server`:

- **king-makers-db**: Internal client database with `check_past_diagnostics` (searches output history for prior analysis) and `register_diagnostic` (logs completed engagements to a JSON registry).
- **king-makers-rag**: Knowledge base search with `search_knowledge_base` (queries ChromaDB vector store for relevant institutional knowledge) and `knowledge_base_stats` (returns index statistics).

### Observability Hooks

PreToolUse and PostToolUse hooks fire on every tool call across all agents:

- Logs tool name, input parameters, execution duration, and tool use ID
- Writes structured JSONL to `output/audit_log.jsonl`
- Prints real-time `[HOOK]` lines to console during execution
- Calculates per-tool execution time in milliseconds

### RAG Knowledge Base

ChromaDB-powered vector store for institutional knowledge:

- Automatic document chunking with paragraph-aware boundaries and configurable overlap
- Deduplication via content hashing (won't re-ingest unchanged documents)
- Similarity search across all past diagnostic briefs
- Seeds automatically on pipeline start from the `output/` directory
- Designed to swap for Supabase pgvector or Pinecone in production

## Quick start

```bash
# Clone and set up
git clone https://github.com/sugarboy21codes/consulting-autopilot.git
cd consulting-autopilot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\Activate   # Windows

pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Run a diagnostic
python main.py https://example.com "struggling with customer retention in their SaaS product"
```

The generated brief lands in the `output/` directory alongside the audit log.

### API Server

```bash
uvicorn api:app --reload --port 8001
```

Endpoints:
- `POST /diagnostics` - Submit a new diagnostic job (returns immediately with job ID)
- `GET /diagnostics` - List all diagnostic jobs
- `GET /diagnostics/{job_id}` - Get job status and results
- `GET /health` - Health check

Interactive API docs at `http://127.0.0.1:8001/docs`.

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

- **Claude Agent SDK** (Python) - Autonomous agent orchestration with tool permissions
- **Custom MCP Servers** - In-process tool servers for internal data access
- **Observability Hooks** - PreToolUse/PostToolUse audit logging
- **ChromaDB** - Local vector database for RAG knowledge base
- **FastAPI** - Async API server with job queue pattern
- **Python 3.10+** - Coordinator logic and CLI

## Project structure

```
consulting-autopilot/
  main.py              # CLI entry point
  api.py               # FastAPI server with async job queue
  coordinator.py       # Python orchestrator for the multi-agent pipeline
  prompts/
    coordinator.py     # Coordinator system prompt
    researcher.py      # Company researcher system prompt
    analyst.py         # Industry analyst system prompt
    writer.py          # Diagnostic writer system prompt
  tools/
    client_db.py       # MCP server: past diagnostics + registry
    knowledge_search.py # MCP server: RAG knowledge base search
  hooks/
    observability.py   # PreToolUse/PostToolUse audit logging hooks
  rag/
    knowledge_base.py  # ChromaDB vector store management
  output/              # Generated diagnostic briefs + audit logs
  requirements.txt     # Dependencies
```

## Roadmap

- [ ] Phase 3: Next.js dashboard frontend
- [ ] Phase 4: Deploy to Render (API) + Vercel (frontend)
- [ ] Supabase pgvector for production RAG storage
- [ ] Additional modes: equity research, job application research, competitor monitoring
- [ ] Agent evaluation harness with automated quality scoring

## Built by

[King Makers](https://kingmakersinc.ca) - AI-native consulting and digital product firm.

## License

## License

Business Source License 1.1 - See [LICENSE](LICENSE) for details.