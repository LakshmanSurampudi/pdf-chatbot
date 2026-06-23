import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.deps import get_current_user_id
from app.models.schemas import ChatMessageOut, ChatRequest
from app.services import pinecone_client
from app.services.embeddings import embed_text
from app.services.embeddings import client as openai_client
from app.services.supabase_client import supabase

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about uploaded PDF documents. "
    "Use only the provided context excerpts to answer. If the answer isn't in the "
    "context, say you don't know. Always be concise and accurate."
)


def _build_context(matches: list[dict]) -> tuple[str, list[dict]]:
    context_parts = []
    sources = []
    for match in matches:
        metadata = match["metadata"]
        context_parts.append(f"[Page {metadata['page']}]\n{metadata['text']}")
        sources.append(
            {
                "document_id": metadata["document_id"],
                "page": metadata["page"],
                "excerpt": metadata["text"][:500],
            }
        )
    return "\n\n---\n\n".join(context_parts), sources


@router.post("")
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    if not request.document_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select at least one document")

    query_embedding = embed_text(request.question)
    matches = pinecone_client.query_chunks(
        user_id, query_embedding, request.document_ids, settings.retrieval_top_k
    )
    context, sources = _build_context(matches)

    history_rows = (
        supabase.table("chat_messages")
        .select("role, content")
        .eq("session_id", request.session_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
        .data
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": row["role"], "content": row["content"]} for row in history_rows]
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {request.question}",
        }
    )

    supabase.table("chat_messages").insert(
        {
            "user_id": user_id,
            "session_id": request.session_id,
            "document_ids": request.document_ids,
            "role": "user",
            "content": request.question,
        }
    ).execute()

    doc_lookup = {
        d["id"]: d["filename"]
        for d in supabase.table("documents")
        .select("id, filename")
        .in_("id", request.document_ids)
        .execute()
        .data
    }
    for source in sources:
        source["filename"] = doc_lookup.get(source["document_id"], "unknown")

    def stream():
        full_answer = ""
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        completion = openai_client.chat.completions.create(
            model=settings.chat_model, messages=messages, stream=True
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                full_answer += delta
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

        message_row = (
            supabase.table("chat_messages")
            .insert(
                {
                    "user_id": user_id,
                    "session_id": request.session_id,
                    "document_ids": request.document_ids,
                    "role": "assistant",
                    "content": full_answer,
                }
            )
            .execute()
            .data[0]
        )
        if sources:
            supabase.table("sources").insert(
                [
                    {
                        "message_id": message_row["id"],
                        "document_id": s["document_id"],
                        "page": s["page"],
                        "excerpt": s["excerpt"],
                    }
                    for s in sources
                ]
            ).execute()
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/{session_id}/history", response_model=list[ChatMessageOut])
def get_history(session_id: str, user_id: str = Depends(get_current_user_id)):
    rows = (
        supabase.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
        .data
    )
    message_ids = [r["id"] for r in rows]
    sources_by_message: dict[str, list[dict]] = {}
    if message_ids:
        source_rows = (
            supabase.table("sources")
            .select("message_id, document_id, page, excerpt, documents(filename)")
            .in_("message_id", message_ids)
            .execute()
            .data
        )
        for row in source_rows:
            sources_by_message.setdefault(row["message_id"], []).append(
                {
                    "document_id": row["document_id"],
                    "filename": (row.get("documents") or {}).get("filename", "unknown"),
                    "page": row["page"],
                    "excerpt": row["excerpt"],
                }
            )

    return [
        {
            "role": row["role"],
            "content": row["content"],
            "sources": sources_by_message.get(row["id"], []),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
