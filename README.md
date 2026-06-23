# PDF-Based AI Chatbot

Upload PDFs, ask questions about their contents, and get answers with page-level
source attribution.

## Architecture

```
Next.js (Vercel)
  - Supabase Auth (login/signup)
  - HTTPS -> FastAPI (Render, verifies Supabase JWT)
                - OpenAI (embeddings + streamed chat)
                - Pinecone (vector chunks, namespaced per user)
                - Supabase Postgres (documents, chat_messages, sources)
```

- **Backend**: `backend/` — FastAPI. Extracts PDF text per page (PyMuPDF, with
  OCR fallback for scanned pages via Tesseract), chunks it, embeds with OpenAI,
  stores vectors in Pinecone (namespaced per user) and document/chat metadata
  in Supabase Postgres. Chat answers stream over SSE and always carry the
  source page(s) + excerpt used.
- **Frontend**: `frontend/` — Next.js (App Router) + Tailwind. Supabase Auth
  for login/signup, a document sidebar for upload/selection, and a chat panel
  with streaming responses and an expandable source panel per answer.

## Setup

### 1. Supabase

1. Create a project at supabase.com.
2. Run `backend/supabase_schema.sql` in the SQL editor.
3. Enable Email auth under Authentication settings.
4. Note down: Project URL, anon key, service role key, and JWT secret
   (Settings -> API).

### 2. Pinecone

Create an account at pinecone.io and grab an API key. The backend
auto-creates the index (`pdf-chatbot` by default, 1536 dims, cosine) on
first startup if it doesn't exist.

### 3. OpenAI

Grab an API key with access to `gpt-4o-mini` and `text-embedding-3-small`
(or change the models in `backend/app/config.py`).

### 4. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate  # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env  # fill in the values from steps 1-3
uvicorn app.main:app --reload
```

Tesseract and Poppler binaries are required locally for OCR fallback
(`brew install tesseract poppler` / `apt-get install tesseract-ocr poppler-utils`).
The Docker image installs these automatically.

### 5. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # fill in Supabase URL/anon key + backend URL
npm run dev
```

## Deployment

- **Backend -> Render**: new Web Service from this repo, root directory
  `backend`, build with the provided `Dockerfile`. Set the same env vars as
  `.env.example`, plus `CORS_ALLOW_ORIGINS` set to your Vercel domain.
- **Frontend -> Vercel**: new project, root directory `frontend`. Set
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
  `NEXT_PUBLIC_API_URL` (your Render backend URL) as env vars.

## Notes / scope (v1)

Implemented: PDF upload (50MB limit), text extraction with OCR fallback for
scanned pages, chunking + embeddings + Pinecone retrieval, streaming chat,
per-answer source attribution (page + excerpt), session-persisted chat
history, multi-PDF support, Supabase auth, Docker for the backend.

Not yet implemented (candidates for v2): citation highlighting inside the
rendered PDF, hybrid (keyword + vector) search, conversation memory
summarization for very long sessions.
