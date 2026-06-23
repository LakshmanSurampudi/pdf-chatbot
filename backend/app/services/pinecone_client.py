from pinecone import Pinecone, ServerlessSpec

from app.config import settings

_pc = Pinecone(api_key=settings.pinecone_api_key)

if settings.pinecone_index_name not in [idx["name"] for idx in _pc.list_indexes()]:
    _pc.create_index(
        name=settings.pinecone_index_name,
        dimension=settings.embedding_dimensions,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = _pc.Index(settings.pinecone_index_name)


def upsert_chunks(user_id: str, document_id: str, vectors: list[dict]) -> None:
    index.upsert(vectors=vectors, namespace=user_id)


def query_chunks(user_id: str, embedding: list[float], document_ids: list[str], top_k: int) -> list[dict]:
    result = index.query(
        vector=embedding,
        top_k=top_k,
        namespace=user_id,
        filter={"document_id": {"$in": document_ids}},
        include_metadata=True,
    )
    return result.get("matches", [])


def delete_document(user_id: str, document_id: str) -> None:
    index.delete(namespace=user_id, filter={"document_id": {"$eq": document_id}})
