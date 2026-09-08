# Ingestion contract

Each approved source document requires a stable `document_id`, source URI or
provenance reference, content checksum, access-scope metadata, ingestion time,
chunking version, embedding-model version and index version. A chunk must retain
its `chunk_id`, `document_id`, order, source locator and access scope.

An ingestion run produces a sanitized manifest. It must be possible to answer:
which source revision created a retrieved chunk, which index served it, and
which access-scope rule admitted it. If that lineage cannot be recovered, the
index is not ready for grounded-answer claims.

Document deletion, permission change, chunking revision and embedding-model
change are invalidation events. The implementation must rebuild or retire the
affected index version before it can be selected for new requests.
