import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import settings
from app.deps import get_current_user_id
from app.models.schemas import DocumentOut
from app.services import pinecone_client
from app.services.embeddings import embed_texts
from app.services.pdf_processing import chunk_pages, extract_pages
from app.services.supabase_client import supabase

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, user_id: str = Depends(get_current_user_id)):
    if file.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File exceeds {settings.max_upload_mb}MB limit")

    pages = extract_pages(pdf_bytes)
    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No extractable text found in PDF")

    document_id = str(uuid.uuid4())

    embeddings = embed_texts([c["text"] for c in chunks])
    vectors = [
        {
            "id": f"{document_id}-{i}",
            "values": embedding,
            "metadata": {
                "document_id": document_id,
                "page": chunk["page"],
                "text": chunk["text"][:2000],
            },
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    pinecone_client.upsert_chunks(user_id, document_id, vectors)

    record = (
        supabase.table("documents")
        .insert(
            {
                "id": document_id,
                "user_id": user_id,
                "filename": file.filename,
                "page_count": len(pages),
            }
        )
        .execute()
    )
    return record.data[0]


@router.get("", response_model=list[DocumentOut])
def list_documents(user_id: str = Depends(get_current_user_id)):
    result = (
        supabase.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user_id: str = Depends(get_current_user_id)):
    pinecone_client.delete_document(user_id, document_id)
    supabase.table("documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
