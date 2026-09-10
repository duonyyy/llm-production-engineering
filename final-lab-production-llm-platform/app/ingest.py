from __future__ import annotations

import argparse
import json
import shutil
import time
import uuid
from pathlib import Path

from app.rag import chunk_text, file_sha256
from app.settings import ROOT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local CPU FAISS index from approved .txt or .md files.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--scope", required=True, help="Server-side scope assigned to every ingested source.")
    parser.add_argument("--embedding-model", required=True, help="Explicit reviewed sentence-transformers model ID.")
    parser.add_argument("--chunk-size", type=int, required=True, help="Chosen after corpus inspection; characters, not tokens.")
    parser.add_argument("--chunk-overlap", type=int, required=True)
    parser.add_argument("--state-dir", type=Path, default=ROOT_DIR / ".runtime")
    parser.add_argument("--replace", action="store_true", help="Explicitly replace an existing index for this knowledge base.")
    args = parser.parse_args()
    if not args.source_dir.is_dir():
        raise SystemExit("source-dir must be an existing approved local directory")
    if not args.knowledge_base_id.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("knowledge-base-id may contain only letters, digits, hyphen and underscore")

    files = sorted(path for path in args.source_dir.rglob("*") if path.suffix.lower() in {".txt", ".md"})
    if not files:
        raise SystemExit("no .txt or .md source files found")
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit("install final-lab-production-llm-platform/requirements.txt before ingestion") from exc

    records = []
    for path in files:
        # Files outside source-dir are never accepted because rglob returns descendants only.
        for position, text in enumerate(chunk_text(path.read_text(encoding="utf-8"), args.chunk_size, args.chunk_overlap)):
            records.append(
                {
                    "chunk_id": f"chunk-{uuid.uuid4().hex}",
                    "document_id": path.relative_to(args.source_dir).as_posix(),
                    "source": path.relative_to(args.source_dir).as_posix(),
                    "source_sha256": file_sha256(path),
                    "scope": args.scope,
                    "text": text,
                    "chunk_position": position,
                }
            )
    if not records:
        raise SystemExit("no non-empty chunks produced")

    model = SentenceTransformer(args.embedding_model, device="cpu")
    vectors = np.asarray(model.encode([record["text"] for record in records], normalize_embeddings=True), dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    target = args.state_dir / "rag" / args.knowledge_base_id
    staging = target.with_name(f"{target.name}.staging-{uuid.uuid4().hex}")
    staging.mkdir(parents=True, exist_ok=False)
    faiss.write_index(index, str(staging / "index.faiss"))
    (staging / "chunks.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n", encoding="utf-8")
    manifest = {
        "knowledge_base_id": args.knowledge_base_id,
        "index_version": f"index-{uuid.uuid4().hex}",
        "created_at": time.time(),
        "embedding_model": args.embedding_model,
        "chunk_size_chars": args.chunk_size,
        "chunk_overlap_chars": args.chunk_overlap,
        "scope": args.scope,
        "source_count": len(files),
        "chunk_count": len(records),
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if target.exists() and not args.replace:
        shutil.rmtree(staging)
        raise SystemExit("target index already exists; inspect its manifest, then rerun only with --replace if replacement is intended")
    if target.exists():
        shutil.rmtree(target)
    staging.replace(target)
    print(json.dumps({"status": "index_created", **manifest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
