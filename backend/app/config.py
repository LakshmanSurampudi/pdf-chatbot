from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "pdf-chatbot"

    supabase_url: str
    supabase_jwt_secret: str
    supabase_service_role_key: str

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chat_model: str = "gpt-4o-mini"

    max_upload_mb: int = 50
    chunk_tokens: int = 500
    chunk_overlap_tokens: int = 50
    retrieval_top_k: int = 6

    cors_allow_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
