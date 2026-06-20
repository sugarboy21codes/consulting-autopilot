FROM python:3.12-slim-bookworm

# Install Node.js 20 LTS (required by Claude Agent SDK's Claude Code CLI subprocess)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ChromaDB's embedding model during build, not at runtime
RUN python -c "\
import chromadb; \
c = chromadb.Client(); \
col = c.get_or_create_collection('warmup'); \
col.add(ids=['warmup'], documents=['warmup text']); \
print('Embedding model cached.')"

# Copy application code
COPY . .

# Ensure output directory exists (gitignored, so not in repo)
RUN mkdir -p output

EXPOSE 8001

# Render sets PORT env var; fall back to 8001 for local testing
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8001}