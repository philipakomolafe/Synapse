# Synapse

Synapse is a multimodal embedding + retrieval engine and a child-first tutor API. It exposes:
- A vector search service (embeddings, document upsert, similarity search)
- A tutoring endpoint that can combine voice, vision, and Socratic guidance
- A minimal web UI for the tutor flow
- Session logging + analytics via Supabase

## Quickstart

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill in your keys.
3. Run the API.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open the UI at `http://localhost:8000`.

## Supabase Setup (Vector Search + Analytics)

Run the SQL in `supabase\schema.sql` in your Supabase SQL editor.

Notes:
- The schema uses `vector(1536)` by default.
- If you change embedding dimensions, update both `OPENAI_EMBEDDING_DIMS` and the schema.
- Analytics tables include `sessions`, `session_events`, and `tutor_interactions`.

## Endpoints

- `GET /` (web UI)
- `GET /health`
- `POST /v1/session/start` (JSON)
- `POST /v1/session/event` (JSON)
- `POST /v1/transcribe` (multipart file `audio`)
- `POST /v1/tts` (JSON)
- `POST /v1/tutor` (JSON)
- `POST /v1/embeddings` (JSON)
- `POST /v1/documents` (JSON)
- `POST /v1/search` (JSON)

### Example: Tutor

```bash
curl -X POST http://localhost:8000/v1/tutor \
  -H "Content-Type: application/json" \
  -d '{
    "question": "I do not understand this math problem",
    "grade_level": "Grade 5",
    "subject": "Math",
    "language": "en"
  }'
```

### Example: Upsert Documents

```bash
curl -X POST http://localhost:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"content": "The water cycle includes evaporation, condensation, and precipitation.", "metadata": {"topic": "science"}}
    ]
  }'
```

### Example: Search

```bash
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is evaporation?", "top_k": 3}'
```

## Notes

- The OpenAI API requires an API key and a billing-enabled account or trial credits.
- Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only.
- Guardrails are enabled by default via `OPENAI_GUARD_ENABLED`.
