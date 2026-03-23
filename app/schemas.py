from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TutorRequest(BaseModel):
    question: str = Field(..., min_length=1)
    image_base64: Optional[str] = None
    image_mime: str = "image/jpeg"
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    language: str = "en"
    use_retrieval: bool = False
    session_id: Optional[str] = None


class TutorResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    guard: Optional[Dict[str, Any]] = None


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = "alloy"
    response_format: str = "mp3"


class TranscribeResponse(BaseModel):
    text: str


class EmbedRequest(BaseModel):
    inputs: List[str] = Field(..., min_length=1)
    store: bool = False
    metadata: Optional[List[Dict[str, Any]]] = None


class EmbedResponse(BaseModel):
    vectors: List[List[float]]


class Document(BaseModel):
    id: Optional[str] = None
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class UpsertDocumentsRequest(BaseModel):
    documents: List[Document] = Field(..., min_length=1)


class UpsertDocumentsResponse(BaseModel):
    ids: List[str]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = 5


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]


class SessionStartRequest(BaseModel):
    device_id: Optional[str] = None
    user_age: Optional[int] = None
    locale: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: str


class SessionEventRequest(BaseModel):
    session_id: str
    event_type: str
    payload: Dict[str, Any] = {}
    client_ts: Optional[str] = None


class SessionEventResponse(BaseModel):
    ok: bool = True
