"""
ChromaDB Vector Store — used by Tech Agent (project similarity) and Fraud Agent (cross-bidder).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tendersense.vectorstore")

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_PROJECTS = "bidder_projects"
COLLECTION_DOCS = "bidder_documents"


class VectorStore:
    """Thin async wrapper around ChromaDB with sentence-transformers embeddings."""

    def __init__(self):
        self._client = None
        self._ef = None

    def _init(self):
        if self._client is not None:
            return
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self._client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        self._ef = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu"
        )
        logger.info(f"ChromaDB initialized at {CHROMA_DIR}")

    # ── public async API ─────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init)
        return True

    async def index_bidder_documents(
        self, bidder_id: str, documents: List[Dict[str, Any]]
    ) -> None:
        """Chunk and embed OCR text from all bidder documents."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._sync_index_documents, bidder_id, documents
        )

    async def search_similar_projects(
        self, query_text: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_search, COLLECTION_PROJECTS, query_text, n_results
        )

    async def cross_bidder_similarity(
        self, bidder_id: str, field: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find other bidders with similar content — fraud detection."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_cross_search, bidder_id, field, n_results
        )

    async def add_project(
        self, bidder_id: str, project_id: str, description: str, metadata: dict
    ) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._sync_add_project, bidder_id, project_id, description, metadata
        )

    # ── sync implementations ─────────────────────────────────────────────────

    def _sync_index_documents(
        self, bidder_id: str, documents: List[Dict[str, Any]]
    ) -> None:
        self._init()
        col = self._client.get_or_create_collection(
            name=COLLECTION_DOCS, embedding_function=self._ef
        )
        for doc in documents:
            text = doc.get("ocr_text", "")
            if not text or len(text) < 20:
                continue
            chunks = self._chunk_text(text, chunk_size=500)
            for i, chunk in enumerate(chunks):
                doc_id = f"{bidder_id}:{doc['id']}:{i}"
                try:
                    col.upsert(
                        ids=[doc_id],
                        documents=[chunk],
                        metadatas=[{
                            "bidder_id": bidder_id,
                            "document_id": str(doc["id"]),
                            "document_type": doc.get("document_type", "other"),
                            "chunk_index": i,
                        }],
                    )
                except Exception as exc:
                    logger.warning(f"Upsert failed for {doc_id}: {exc}")

    def _sync_add_project(
        self, bidder_id: str, project_id: str, description: str, metadata: dict
    ) -> None:
        self._init()
        col = self._client.get_or_create_collection(
            name=COLLECTION_PROJECTS, embedding_function=self._ef
        )
        meta = {**metadata, "bidder_id": bidder_id, "project_id": project_id}
        col.upsert(ids=[f"{bidder_id}:{project_id}"], documents=[description], metadatas=[meta])

    def _sync_search(
        self, collection_name: str, query: str, n: int
    ) -> List[Dict[str, Any]]:
        self._init()
        try:
            col = self._client.get_or_create_collection(
                name=collection_name, embedding_function=self._ef
            )
            res = col.query(query_texts=[query], n_results=min(n, max(col.count(), 1)))
            results = []
            for i, doc in enumerate(res["documents"][0]):
                results.append({
                    "text": doc,
                    "metadata": res["metadatas"][0][i],
                    "distance": res["distances"][0][i] if res.get("distances") else None,
                })
            return results
        except Exception as exc:
            logger.warning(f"VectorStore search failed: {exc}")
            return []

    def _sync_cross_search(
        self, bidder_id: str, field: str, n: int
    ) -> List[Dict[str, Any]]:
        self._init()
        try:
            col = self._client.get_or_create_collection(
                name=COLLECTION_DOCS, embedding_function=self._ef
            )
            # Get this bidder's docs as query
            bidder_docs = col.get(
                where={"bidder_id": bidder_id},
                limit=3,
                include=["documents"],
            )
            if not bidder_docs["documents"]:
                return []
            query_text = " ".join(bidder_docs["documents"][:3])
            res = col.query(
                query_texts=[query_text],
                n_results=n + 1,
                where={"bidder_id": {"$ne": bidder_id}},
            )
            return [
                {"text": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(
                    res["documents"][0],
                    res["metadatas"][0],
                    res.get("distances", [[None] * n])[0],
                )
            ]
        except Exception as exc:
            logger.warning(f"Cross-bidder search failed: {exc}")
            return []

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500) -> List[str]:
        words = text.split()
        chunks, current = [], []
        for word in words:
            current.append(word)
            if len(current) >= chunk_size:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
        return chunks
