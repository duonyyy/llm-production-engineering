from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class RAGUnavailable(RuntimeError):
    pass


class InsufficientEvidence(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source: str
    text: str
    score: float
    index_version: str


@dataclass(frozen=True)
class RetrievalResult:
    retrieval_id: str
    knowledge_base_id: str
    index_version: str
    embedding_ms: float
    retrieval_ms: float
    chunks: tuple[RetrievedChunk, ...]


class LocalFaissRetriever:
    """CPU-only local RAG backend. It loads a selected embedding model only when used."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir / "rag"
        self._models: dict[str, Any] = {}

    def _paths(self, knowledge_base_id: str) -> tuple[Path, Path, Path]:
        root = self.state_dir / knowledge_base_id
        return root / "index.faiss", root / "chunks.jsonl", root / "manifest.json"

    def _model(self, model_id: str):
        if not model_id:
            raise RAGUnavailable("embedding_model_not_configured")
        if model_id not in self._models:
            try:
                from sentence_transformers import SentenceTransformer

                self._models[model_id] = SentenceTransformer(model_id, device="cpu")
            except Exception as exc:  # dependency, cache, or model failures are fail-closed
                raise RAGUnavailable(f"embedding_model_unavailable:{type(exc).__name__}") from exc
        return self._models[model_id]

    def retrieve(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        top_k: int,
        allowed_scopes: frozenset[str],
        embedding_model: str,
    ) -> RetrievalResult:
        index_path, chunks_path, manifest_path = self._paths(knowledge_base_id)
        if not index_path.exists() or not chunks_path.exists() or not manifest_path.exists():
            raise RAGUnavailable("knowledge_base_index_unavailable")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("embedding_model") != embedding_model:
                raise RAGUnavailable("embedding_model_does_not_match_index_manifest")
            import faiss
            import numpy as np

            chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line]
            if not chunks:
                raise RAGUnavailable("knowledge_base_contains_no_chunks")
            embed_started = time.perf_counter()
            vector = self._model(embedding_model).encode([query], normalize_embeddings=True)
            embedding_ms = (time.perf_counter() - embed_started) * 1000
            index = faiss.read_index(str(index_path))
            # Over-fetch only within this knowledge-base index, then filter before any context is built.
            retrieval_started = time.perf_counter()
            scores, positions = index.search(np.asarray(vector, dtype="float32"), min(len(chunks), top_k * 20))
            retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        except RAGUnavailable:
            raise
        except Exception as exc:
            raise RAGUnavailable(f"index_load_or_query_failed:{type(exc).__name__}") from exc

        found: list[RetrievedChunk] = []
        for score, position in zip(scores[0], positions[0]):
            if position < 0:
                continue
            item = chunks[int(position)]
            if item.get("scope") not in allowed_scopes:
                continue
            found.append(
                RetrievedChunk(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    source=item["source"],
                    text=item["text"],
                    score=float(score),
                    index_version=manifest["index_version"],
                )
            )
            if len(found) == top_k:
                break
        if not found:
            raise InsufficientEvidence("no_authorized_evidence")
        return RetrievalResult(
            retrieval_id=f"retrieval-{uuid.uuid4().hex}",
            knowledge_base_id=knowledge_base_id,
            index_version=manifest["index_version"],
            embedding_ms=round(embedding_ms, 3),
            retrieval_ms=round(retrieval_ms, 3),
            chunks=tuple(found),
        )


def build_grounded_messages(messages: list[dict[str, str]], result: RetrievalResult) -> list[dict[str, str]]:
    evidence = "\n\n".join(
        f"[source:{chunk.document_id}#{chunk.chunk_id}]\n{chunk.text}" for chunk in result.chunks
    )
    instruction = (
        "Answer only from the authorized evidence below. If it does not support an answer, say so. "
        "Cite each factual claim using the exact [source:document_id#chunk_id] identifier.\n\n"
        f"AUTHORIZED EVIDENCE (index={result.index_version}):\n{evidence}"
    )
    return [{"role": "system", "content": instruction}, *messages]


def citations(result: RetrievalResult) -> list[dict[str, str]]:
    return [
        {"document_id": chunk.document_id, "chunk_id": chunk.chunk_id, "source": chunk.source}
        for chunk in result.chunks
    ]


def chunk_text(text: str, size: int, overlap: int) -> Iterable[str]:
    if size < 100 or overlap < 0 or overlap >= size:
        raise ValueError("chunk_size must be at least 100 and overlap must be non-negative and smaller than size")
    normalized = " ".join(text.split())
    cursor = 0
    while cursor < len(normalized):
        stop = min(len(normalized), cursor + size)
        if stop < len(normalized):
            boundary = normalized.rfind(" ", cursor, stop)
            stop = boundary if boundary > cursor else stop
        yield normalized[cursor:stop]
        if stop == len(normalized):
            break
        cursor = stop - overlap


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
