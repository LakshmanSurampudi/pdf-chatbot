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

## Design Decisions

### Chunking strategy

Text is extracted per page (`backend/app/services/pdf_processing.py`) using
PyMuPDF, with a Tesseract OCR fallback for pages that have no extractable
text (scanned/image-only pages). Each page is then split independently into
overlapping chunks by token count (`tiktoken`, `cl100k_base` encoding):

- **Chunk size**: 500 tokens (`CHUNK_TOKENS`)
- **Overlap**: 50 tokens (`CHUNK_OVERLAP_TOKENS`)

Chunking is done per page rather than across page boundaries so every chunk
has one unambiguous source page, which is what makes page-level citation
possible. The overlap means a sentence split across two chunks still has a
good chance of appearing whole in at least one of them, which improves
recall for nearby-boundary queries at the cost of slightly more storage and
embedding calls.

### Embedding model choice

Both chunks (at upload) and questions (at query time) are embedded with
`text-embedding-3-small` (1536 dimensions). It was chosen over
`text-embedding-3-large` or the older `text-embedding-ada-002` as the best
fit for this use case: it's materially cheaper and lower-latency than the
`-large` variant while still outperforming `ada-002` on retrieval quality,
which matters more here than squeezing out the last bit of accuracy given
the chunk sizes and corpus sizes involved. Using the same model for both
documents and queries is required for the cosine similarity comparison in
retrieval to be meaningful.

### Retrieval approach

Embeddings are stored in Pinecone (cosine similarity, serverless index),
namespaced per `user_id` — this is the multi-tenancy boundary, so one
user's vectors are never visible to another's queries even though they
share an index. Each vector carries `document_id` and `page` as metadata.

At query time (`backend/app/routers/chat.py`):

1. The question is embedded once.
2. Pinecone is queried for the top **6** nearest chunks (`RETRIEVAL_TOP_K`),
   filtered to only the documents the user has selected in the UI
   (`document_id $in [...]`) — so retrieval is scoped to whatever subset of
   their library they're currently chatting against, not their whole
   account.
3. Matched chunks become both the LLM context and the "sources" returned to
   the client (page number + a 500-character excerpt) for citation in the
   UI.

### Prompt design

The system prompt is fixed and deliberately narrow: answer only from the
provided context, say "I don't know" if the answer isn't there, stay
concise. This is the main lever against hallucination, since the model is
explicitly told not to fall back on outside knowledge.

Each retrieved chunk is tagged with `[Page N]` and joined with `---`
separators before being inserted into the prompt, so page provenance is
visible to the model, not just attached afterward in the API response.
The full prior conversation for the session is replayed as alternating
user/assistant turns ahead of the current question (no summarization), so
the model has multi-turn memory. The current turn is formatted as:

```
Context:
[Page 1]
<chunk text>

---

[Page 2]
<chunk text>

Question: <user's question>
```

Sources are streamed to the client as a separate SSE event *before* the
model starts generating, so the UI can render citations immediately rather
than waiting for the full streamed answer.

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
