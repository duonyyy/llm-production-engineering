from __future__ import annotations

import hmac
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.inference import InferenceUnavailable, VLLMClient
from app.observability import LATENCY, REQUESTS, RETRIEVAL, TOOL_EVENTS, RecentMetrics, SafeEventLog
from app.rag import InsufficientEvidence, LocalFaissRetriever, RAGUnavailable, build_grounded_messages, citations
from app.settings import Settings
from app.store import AuditStore


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class RAGOptions(BaseModel):
    mode: Literal["required"]
    knowledge_base_id: str = Field(min_length=1, max_length=80)
    top_k: int = Field(default=4, ge=1, le=10)
    metadata_filters: dict[str, str] | None = None


class ChatRequest(BaseModel):
    request_id: str | None = Field(default=None, max_length=128)
    model: str
    messages: list[Message] = Field(min_length=1, max_length=32)
    max_tokens: int = Field(ge=1, le=512)
    stream: bool = False
    router_mode: Literal["colocated", "pd"] = "colocated"
    timeout_ms: int = Field(ge=1, le=120000)
    workload_label: Literal[
        "short_input_short_output", "long_input_short_output", "short_input_long_output", "long_input_long_output", "repeated_prefix", "mixed"
    ]
    rag: RAGOptions | None = None

    @field_validator("request_id")
    @classmethod
    def opaque_request_id(cls, value: str | None) -> str | None:
        if value is not None and not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("request_id must be opaque alphanumeric, hyphen or underscore")
        return value


class ToolRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=160)
    arguments: dict[str, int | str] = Field(default_factory=dict)


class Runtime:
    def __init__(self, settings: Settings) -> None:
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        self.vllm = VLLMClient(settings.vllm_base_url, settings.timeout_ms)
        self.rag = LocalFaissRetriever(settings.state_dir)
        self.audit = AuditStore(settings.state_dir / "agent_state.sqlite3")
        self.events = SafeEventLog(settings.state_dir / "logs" / "final-lab.jsonl")
        self.recent = RecentMetrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = Runtime(Settings.from_env())
    app.state.runtime = service
    try:
        yield
    finally:
        service.events.close()


app = FastAPI(title="Final Lab Single-Node LLM Platform", version="0.1.0", lifespan=lifespan)


def runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def request_id(payload: ChatRequest, header_value: str | None) -> str:
    candidate = header_value or payload.request_id
    return candidate or f"req-{uuid.uuid4().hex}"


def authenticated(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    configured = runtime(request).settings.api_token
    if not configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication_not_configured")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_failed")
    return runtime(request).settings.principal


def bounded_error(code: str, request_id_value: str, http_status: int, **metadata: Any) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": code, "request_id": request_id_value, "execution_mode": "LOCAL", **metadata},
        headers={"X-Request-ID": request_id_value, "X-Final-Lab-Route": "colocated"},
    )


def upstream_payload(payload: ChatRequest, messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "model": payload.model,
        "messages": messages,
        "max_tokens": payload.max_tokens,
        "stream": payload.stream,
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "final-lab-api"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    service = runtime(request)
    ready = bool(service.settings.api_token) and await service.vllm.models_ready()
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "auth_configured": bool(service.settings.api_token), "vllm_reachable": ready},
    )


@app.get("/metrics")
async def metrics() -> StreamingResponse:
    return StreamingResponse(iter([generate_latest()]), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatRequest,
    request: Request,
    x_request_id: Annotated[str | None, Header()] = None,
    _: str = Depends(authenticated),
):
    service = runtime(request)
    rid = request_id(payload, x_request_id)
    started = time.perf_counter()
    route = "colocated"
    service.events.emit("request_received", request_id=rid, route=route, workload_label=payload.workload_label)
    if payload.router_mode != "colocated":
        return bounded_error("advanced_route_not_available_in_local_mode", rid, 422)
    if payload.model != service.settings.model_id:
        return bounded_error("model_not_allowed_by_local_profile", rid, 422)

    messages = [message.model_dump() for message in payload.messages]
    retrieval = None
    if payload.rag is not None:
        if payload.stream:
            return bounded_error("rag_streaming_not_implemented", rid, 422)
        if payload.rag.knowledge_base_id not in service.settings.allowed_knowledge_bases:
            return bounded_error("knowledge_base_authorization_denied", rid, 403)
        query = next((message.content for message in reversed(payload.messages) if message.role == "user"), "")
        try:
            retrieval = service.rag.retrieve(
                knowledge_base_id=payload.rag.knowledge_base_id,
                query=query,
                top_k=payload.rag.top_k,
                allowed_scopes=service.settings.allowed_scopes,
                embedding_model=os.getenv("FINAL_RAG_EMBEDDING_MODEL", ""),
            )
            RETRIEVAL.labels("completed").observe(retrieval.retrieval_ms / 1000)
            service.events.emit(
                "retrieval_completed",
                request_id=rid,
                retrieval_id=retrieval.retrieval_id,
                knowledge_base_id=retrieval.knowledge_base_id,
                index_version=retrieval.index_version,
                retrieved_chunk_count=len(retrieval.chunks),
            )
            messages = build_grounded_messages(messages, retrieval)
        except (RAGUnavailable, InsufficientEvidence) as exc:
            RETRIEVAL.labels("abstained").observe(0)
            elapsed = (time.perf_counter() - started) * 1000
            REQUESTS.labels(route, "insufficient_evidence", "LOCAL").inc()
            LATENCY.labels(route, "insufficient_evidence", "LOCAL").observe(elapsed / 1000)
            service.recent.add(route, "insufficient_evidence", elapsed)
            service.events.emit("retrieval_abstained", request_id=rid, error_class=type(exc).__name__)
            return bounded_error("insufficient_evidence", rid, 424, retrieval_id=f"retrieval-{uuid.uuid4().hex}")

    request_to_vllm = upstream_payload(payload, messages)
    try:
        if payload.stream:
            async def body():
                async for chunk in service.vllm.stream(request_to_vllm, rid):
                    yield chunk

            return StreamingResponse(body(), media_type="text/event-stream", headers={"X-Request-ID": rid, "X-Final-Lab-Route": route})
        response = await service.vllm.completion(request_to_vllm, rid)
    except InferenceUnavailable as exc:
        elapsed = (time.perf_counter() - started) * 1000
        REQUESTS.labels(route, "failed", "LOCAL").inc()
        LATENCY.labels(route, "failed", "LOCAL").observe(elapsed / 1000)
        service.recent.add(route, "failed", elapsed)
        service.events.emit("inference_failed", request_id=rid, error_class=type(exc).__name__)
        return bounded_error("inference_unavailable", rid, 502, llm_request_id=rid, router_request_id=rid)

    elapsed = (time.perf_counter() - started) * 1000
    response["final_lab"] = {
        "execution_mode": "LOCAL",
        "llm_request_id": rid,
        "router_request_id": rid,
        "retrieval_id": retrieval.retrieval_id if retrieval else None,
        "citations": citations(retrieval) if retrieval else [],
        "metric_availability": {"ttft_ms": "NA", "tpot_ms": "NA", "e2e_ms": round(elapsed, 3)},
    }
    REQUESTS.labels(route, "completed", "LOCAL").inc()
    LATENCY.labels(route, "completed", "LOCAL").observe(elapsed / 1000)
    service.recent.add(route, "completed", elapsed)
    service.events.emit("response_terminal", request_id=rid, terminal_status="completed", retrieval_id=retrieval.retrieval_id if retrieval else None)
    return JSONResponse(response, headers={"X-Request-ID": rid, "X-Final-Lab-Route": route})


@app.post("/v1/operations/{tool_name}")
async def operations(
    tool_name: Literal["get_model_health", "get_recent_metrics"],
    payload: ToolRequest,
    request: Request,
    _: str = Depends(authenticated),
):
    service = runtime(request)
    task_id = f"task-{uuid.uuid4().hex}"
    tool_call_id = f"tool-{uuid.uuid4().hex}"
    if not service.audit.claim_idempotency(payload.idempotency_key):
        TOOL_EVENTS.labels(tool_name, "duplicate_denied").inc()
        return bounded_error("duplicate_tool_retry_denied", task_id, 409, task_id=task_id, tool_call_id=tool_call_id)
    try:
        if tool_name == "get_model_health":
            if payload.arguments and set(payload.arguments) - {"component"}:
                raise ValueError("invalid_tool_arguments")
            result = {"vllm_reachable": await service.vllm.models_ready(), "route": "colocated"}
        else:
            if set(payload.arguments) - {"window_minutes"}:
                raise ValueError("invalid_tool_arguments")
            window = int(payload.arguments.get("window_minutes", 5))
            if not 1 <= window <= 60:
                raise ValueError("window_minutes_out_of_range")
            result = service.recent.summary(window)
        service.audit.append_event(task_id, tool_call_id, "tool_call_completed", {"tool": tool_name, "disposition": "read_only_completed"})
        TOOL_EVENTS.labels(tool_name, "completed").inc()
        return {"status": "completed", "task_id": task_id, "tool_call_id": tool_call_id, "tool": tool_name, "result": result, "execution_mode": "LOCAL"}
    except Exception as exc:
        service.audit.append_event(task_id, tool_call_id, "tool_call_failed_closed", {"tool": tool_name, "error_class": type(exc).__name__})
        TOOL_EVENTS.labels(tool_name, "failed_closed").inc()
        return bounded_error("agent_failed_closed", task_id, 422, task_id=task_id, tool_call_id=tool_call_id)
