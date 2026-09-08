# RAG boundary

## Status and role

This is a single-node RAG design, not a claim that a knowledge base, embedding
model, index, retrieval evaluation, or grounded-answer service has run. RAG
adds evidence to a request before vLLM generates; it does not replace the LLM
serving boundary.

## Local data path

```text
approved documents
  -> validate provenance and access metadata
  -> normalize and chunk
  -> CPU embedding
  -> local FAISS index + metadata store

grounded request
  -> authorization/document-scope filter
  -> CPU query embedding
  -> retrieve top-k authorized chunks
  -> context builder with source identifiers
  -> vLLM generation with citations or insufficient-evidence abstention
```

The GTX 3050 4 GB is reserved for the small vLLM serving profile. Embedding,
indexing and FAISS retrieval use CPU/RAM by default so they do not compete for
VRAM. A reranker is not enabled by default; add one only after a measured
retrieval-quality comparison justifies its latency and memory cost.

## Required controls

- Select the embedding model only after recording corpus language, license and
  evaluation set; `embedding_model: NOT_SELECTED` is intentional in the initial
  scaffold.
- Version documents, chunks, embedding model and index together. Rebuild or
  invalidate the index when any of those inputs changes.
- Enforce authorization and document scope before data is exposed to the LLM.
  Post-filtering already retrieved content is not a sufficient isolation
  control.
- Preserve `retrieval_id`, knowledge-base version and source identifiers. Do
  not log raw documents, prompts, access tokens or private metadata.
- A request with `rag.mode=required` must return an insufficient-evidence state
  if authorized evidence is unavailable; it must not silently become plain LLM
  inference.

## Evidence needed before quality claims

Retrieval and generation must be evaluated separately. A real evaluation needs
a documented corpus, labeled question/source pairs, index version, retrieval
raw results, answer/citation review and latency records. Until then,
Recall@k, MRR/nDCG, faithfulness, citation coverage and freshness are `NA` or
`NOT_RUN`.
