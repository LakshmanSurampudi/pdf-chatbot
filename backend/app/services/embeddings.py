from openai import OpenAI

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
