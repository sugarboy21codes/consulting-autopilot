"""
King Makers Knowledge Base (RAG)

ChromaDB-powered vector store that embeds past diagnostic briefs
and internal knowledge documents. Enables the analyst agent to
retrieve relevant institutional knowledge before doing web research.

This demonstrates RAG pipeline implementation including document chunking,
vector embedding, similarity search, and integration with agent architectures.
"""

import hashlib
from pathlib import Path

import chromadb


class KingMakersKnowledgeBase:
    """
    Vector store for King Makers' institutional knowledge.

    Embeds past diagnostic briefs and knowledge documents into
    ChromaDB for retrieval during future analyses. In production,
    this would use Supabase pgvector or Pinecone instead of
    local ChromaDB storage.
    """

    def __init__(self, persist_dir: str = ".chromadb"):
        """
        Initialize the knowledge base.

        Args:
            persist_dir: Directory for ChromaDB's local storage.
        """
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="king_makers_knowledge",
            metadata={"description": "Past diagnostic briefs and industry knowledge"},
        )

    def ingest_document(self, filepath: Path) -> int:
        """
        Read a document, chunk it, and embed chunks into the vector store.

        Args:
            filepath: Path to a markdown document to ingest.

        Returns:
            Number of chunks created from this document.
        """
        content = filepath.read_text(encoding="utf-8")
        filename = filepath.name

        # Generate a stable document ID from the file path
        doc_id = hashlib.md5(str(filepath).encode()).hexdigest()[:12]

        # Check if already ingested (avoid duplicates)
        existing = self.collection.get(where={"source_file": filename})
        if existing and existing["ids"]:
            return 0  # Already ingested

        # Chunk the document
        chunks = self._chunk_document(content, chunk_size=500, overlap=50)

        if not chunks:
            return 0

        # Prepare batch for ChromaDB
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source_file": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        # Add to collection (ChromaDB handles embedding automatically)
        self.collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    def ingest_directory(self, directory: Path) -> dict:
        """
        Ingest all markdown files in a directory.

        Args:
            directory: Path to scan for .md files.

        Returns:
            Summary of ingestion results.
        """
        results = {"files_processed": 0, "chunks_created": 0, "files_skipped": 0}

        if not directory.exists():
            return results

        for md_file in directory.glob("*.md"):
            chunks_added = self.ingest_document(md_file)
            if chunks_added > 0:
                results["files_processed"] += 1
                results["chunks_created"] += chunks_added
            else:
                results["files_skipped"] += 1

        return results

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """
        Search the knowledge base for chunks relevant to a query.

        Args:
            query_text: The search query (natural language).
            n_results: Maximum number of results to return.

        Returns:
            List of matching chunks with metadata and relevance scores.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(n_results, self.collection.count()),
        )

        # Format results for easy consumption
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "chunk_id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "source_file": results["metadatas"][0][i].get("source_file", "unknown"),
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })

        return formatted

    def get_stats(self) -> dict:
        """Return statistics about the knowledge base."""
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection.name,
        }

    @staticmethod
    def _chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """
        Split a document into overlapping chunks by paragraph boundaries.

        Uses paragraph breaks as natural split points, then enforces
        the chunk_size limit. Overlap ensures context isn't lost at
        chunk boundaries.

        Args:
            text: Full document text.
            chunk_size: Target words per chunk.
            overlap: Words of overlap between consecutive chunks.

        Returns:
            List of text chunks.
        """
        # Split into paragraphs first (natural boundaries)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = []
        current_word_count = 0

        for paragraph in paragraphs:
            paragraph_words = len(paragraph.split())

            # If adding this paragraph exceeds chunk_size, save current and start new
            if current_word_count + paragraph_words > chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)

                # Keep overlap: take the last paragraph(s) as overlap
                overlap_words = 0
                overlap_paragraphs = []
                for p in reversed(current_chunk):
                    p_words = len(p.split())
                    if overlap_words + p_words <= overlap:
                        overlap_paragraphs.insert(0, p)
                        overlap_words += p_words
                    else:
                        break

                current_chunk = overlap_paragraphs
                current_word_count = overlap_words

            current_chunk.append(paragraph)
            current_word_count += paragraph_words

        # Don't forget the last chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks