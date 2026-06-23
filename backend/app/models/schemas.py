from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    page_count: int
    uploaded_at: datetime


class ChatRequest(BaseModel):
    session_id: str
    question: str
    document_ids: list[str]


class SourceOut(BaseModel):
    document_id: str
    filename: str
    page: int
    excerpt: str


class ChatMessageOut(BaseModel):
    role: str
    content: str
    sources: list[SourceOut] = []
    created_at: datetime
