import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.prompts import GUARD_PROMPT, MODE_GUIDES, REVISION_PROMPT, TUTOR_PROMPT
from app.schemas import (
    AdminSummaryResponse,
    EmbedRequest,
    EmbedResponse,
    SearchRequest,
    SearchResponse,
    SessionEventRequest,
    SessionEventResponse,
    SessionStartRequest,
    SessionStartResponse,
    TranscribeResponse,
    TTSRequest,
    TutorRequest,
    TutorResponse,
    UpsertDocumentsRequest,
    UpsertDocumentsResponse,
)
from app.services.openai_client import get_openai_client
from app.services.supabase_client import get_supabase_client
from app.settings import settings

app = FastAPI(title="Synapse API", version="0.3.0")

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


def require_openai():
    try:
        return get_openai_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_supabase(required: bool = False):
    client = get_supabase_client()
    if required and client is None:
        raise HTTPException(status_code=501, detail="Supabase is not configured")
    return client


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_guard_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
    return {}


def run_guard(client, answer_text: str) -> Dict[str, Any]:
    if not settings.openai_guard_enabled:
        return {"safe": True, "teaches": True, "notes": "guard_disabled"}

    try:
        response = client.responses.create(
            model=settings.openai_guard_model,
            input=[{
                "role": "user",
                "content": [{"type": "input_text", "text": f"{GUARD_PROMPT}\n\nResponse:\n{answer_text}"}]
            }],
        )
        guard_text = getattr(response, "output_text", "")
        guard_data = parse_guard_json(guard_text)
        if guard_data:
            return guard_data
    except Exception:
        pass

    return {"safe": True, "teaches": False, "notes": "guard_error"}


def revise_answer(client, original: str, notes: str) -> str:
    response = client.responses.create(
        model=settings.openai_tutor_model,
        input=[{
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": f"{REVISION_PROMPT}\n\nNotes: {notes}\n\nOriginal:\n{original}"
            }]
        }],
    )
    revised = getattr(response, "output_text", None)
    return revised or original


@app.get("/")
def index():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="UI not found")


@app.get("/admin")
def admin_dashboard():
    admin_path = static_dir / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    raise HTTPException(status_code=404, detail="Admin UI not found")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/session/start", response_model=SessionStartResponse)
def start_session(request: SessionStartRequest) -> SessionStartResponse:
    supabase = get_supabase(required=True)
    session_id = str(uuid4())
    supabase.table("sessions").insert({
        "id": session_id,
        "device_id": request.device_id,
        "user_age": request.user_age,
        "locale": request.locale,
        "created_at": utc_now(),
    }).execute()
    return SessionStartResponse(session_id=session_id)


@app.post("/v1/session/event", response_model=SessionEventResponse)
def log_session_event(request: SessionEventRequest) -> SessionEventResponse:
    supabase = get_supabase(required=True)
    supabase.table("session_events").insert({
        "session_id": request.session_id,
        "event_type": request.event_type,
        "payload": request.payload,
        "client_ts": request.client_ts,
        "received_at": utc_now(),
    }).execute()
    return SessionEventResponse(ok=True)


@app.get("/v1/admin/summary", response_model=AdminSummaryResponse)
def admin_summary() -> AdminSummaryResponse:
    supabase = get_supabase(required=True)

    sessions_resp = supabase.table("sessions").select("id", count="exact").execute()
    total_sessions = sessions_resp.count or 0

    interactions_resp = supabase.table("tutor_interactions").select("id", count="exact").execute()
    total_interactions = interactions_resp.count or 0

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_24_resp = (
        supabase.table("tutor_interactions")
        .select("id", count="exact")
        .gte("created_at", since)
        .execute()
    )
    interactions_24h = recent_24_resp.count or 0

    recent_resp = (
        supabase.table("tutor_interactions")
        .select("session_id,question,subject,mode,created_at,has_image")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    recent_interactions = recent_resp.data or []

    return AdminSummaryResponse(
        total_sessions=total_sessions,
        total_interactions=total_interactions,
        interactions_24h=interactions_24h,
        recent_interactions=recent_interactions,
    )


@app.post("/v1/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscribeResponse:
    client = require_openai()
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = audio.filename or "audio.wav"

    try:
        result = client.audio.transcriptions.create(
            model=settings.openai_stt_model,
            file=file_obj,
            response_format="text",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    text = getattr(result, "text", None)
    if text is None:
        text = result if isinstance(result, str) else str(result)
    return TranscribeResponse(text=text)


@app.post("/v1/tts")
def text_to_speech(request: TTSRequest):
    client = require_openai()

    media_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
    }
    media_type = media_types.get(request.response_format, "audio/mpeg")

    def stream_audio():
        with client.audio.speech.with_streaming_response.create(
            model=settings.openai_tts_model,
            voice=request.voice,
            input=request.text,
            response_format=request.response_format,
        ) as response:
            for chunk in response.iter_bytes():
                yield chunk

    return StreamingResponse(stream_audio(), media_type=media_type)


@app.post("/v1/embeddings", response_model=EmbedResponse)
def create_embeddings(request: EmbedRequest) -> EmbedResponse:
    client = require_openai()
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=request.inputs,
        dimensions=settings.openai_embedding_dims,
    )
    vectors = [item.embedding for item in response.data]

    if request.store:
        supabase = get_supabase(required=True)
        rows: List[Dict[str, Any]] = []
        for idx, content in enumerate(request.inputs):
            meta = None
            if request.metadata and idx < len(request.metadata):
                meta = request.metadata[idx]
            rows.append({
                "content": content,
                "metadata": meta,
                "embedding": vectors[idx],
            })
        supabase.table("documents").insert(rows).execute()

    return EmbedResponse(vectors=vectors)


@app.post("/v1/documents", response_model=UpsertDocumentsResponse)
def upsert_documents(request: UpsertDocumentsRequest) -> UpsertDocumentsResponse:
    client = require_openai()
    supabase = get_supabase(required=True)

    contents = [doc.content for doc in request.documents]
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=contents,
        dimensions=settings.openai_embedding_dims,
    )
    vectors = [item.embedding for item in response.data]

    rows: List[Dict[str, Any]] = []
    for doc, vector in zip(request.documents, vectors):
        row: Dict[str, Any] = {
            "content": doc.content,
            "metadata": doc.metadata,
            "embedding": vector,
        }
        if doc.id:
            row["id"] = doc.id
        rows.append(row)

    result = supabase.table("documents").upsert(rows).execute()
    ids = [row.get("id") for row in (result.data or []) if row.get("id")]
    if not ids:
        ids = [doc.id for doc in request.documents if doc.id]

    return UpsertDocumentsResponse(ids=ids)


@app.post("/v1/search", response_model=SearchResponse)
def search_documents(request: SearchRequest) -> SearchResponse:
    client = require_openai()
    supabase = get_supabase(required=True)

    embedding_response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=request.query,
        dimensions=settings.openai_embedding_dims,
    )
    query_embedding = embedding_response.data[0].embedding

    response = supabase.rpc(
        "match_documents",
        {"query_embedding": query_embedding, "match_count": request.top_k},
    ).execute()

    return SearchResponse(results=response.data or [])


@app.post("/v1/tutor", response_model=TutorResponse)
def tutor(request: TutorRequest) -> TutorResponse:
    client = require_openai()
    sources: List[Dict[str, Any]] = []

    use_retrieval = request.use_retrieval or bool(request.mode) or bool(request.subject)
    if use_retrieval:
        supabase = get_supabase(required=True)
        embedding_response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=request.question,
            dimensions=settings.openai_embedding_dims,
        )
        query_embedding = embedding_response.data[0].embedding
        retrieval = supabase.rpc(
            "match_documents",
            {"query_embedding": query_embedding, "match_count": request.retrieval_top_k},
        ).execute()
        sources = retrieval.data or []

    context_text = ""
    if sources:
        snippets = [f"- {item.get('content', '')}" for item in sources]
        context_text = "\n\nRelevant notes:\n" + "\n".join(snippets)

    mode_hint = MODE_GUIDES.get((request.mode or "").lower(), "")
    if mode_hint:
        mode_hint = f"Mode guidance: {mode_hint}\n"

    prompt = (
        f"{TUTOR_PROMPT}\n\n"
        f"Student question: {request.question}\n"
        f"Grade level: {request.grade_level or 'unknown'}\n"
        f"Subject: {request.subject or 'unknown'}\n"
        f"Mode: {request.mode or 'general'}\n"
        f"Language: {request.language}\n"
        f"{mode_hint}"
        f"{context_text}"
    ).strip()

    content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    if request.image_base64:
        image_data = request.image_base64
        if not image_data.startswith("data:"):
            image_data = f"data:{request.image_mime};base64,{image_data}"
        content.append({"type": "input_image", "image_url": image_data})

    try:
        response = client.responses.create(
            model=settings.openai_tutor_model,
            input=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Tutor request failed: {exc}")

    answer = getattr(response, "output_text", None) or str(response)
    guard = run_guard(client, answer)

    retries = 0
    while settings.openai_guard_enabled and retries < settings.openai_guard_max_retries:
        if guard.get("safe") is True and guard.get("teaches") is True:
            break
        answer = revise_answer(client, answer, guard.get("notes", ""))
        guard = run_guard(client, answer)
        retries += 1

    if request.session_id:
        supabase = get_supabase(required=False)
        if supabase is not None:
            supabase.table("tutor_interactions").insert({
                "session_id": request.session_id,
                "question": request.question,
                "answer": answer,
                "grade_level": request.grade_level,
                "subject": request.subject,
                "mode": request.mode,
                "language": request.language,
                "has_image": bool(request.image_base64),
                "guard": guard,
                "created_at": utc_now(),
            }).execute()

    return TutorResponse(answer=answer, sources=sources, guard=guard)
