from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, documents

app = FastAPI(title="PDF Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
