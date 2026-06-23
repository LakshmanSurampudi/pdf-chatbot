import io

import fitz  # PyMuPDF
import tiktoken
from pdf2image import convert_from_bytes
from pytesseract import image_to_string

from app.config import settings

_encoder = tiktoken.get_encoding("cl100k_base")


def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Return text per page, falling back to OCR for pages with no extractable text."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[str] = []
    ocr_needed: list[int] = []

    for page_number, page in enumerate(doc):
        text = page.get_text().strip()
        pages.append(text)
        if not text:
            ocr_needed.append(page_number)

    doc.close()

    if ocr_needed:
        images = convert_from_bytes(pdf_bytes)
        for page_number in ocr_needed:
            pages[page_number] = image_to_string(images[page_number]).strip()

    return pages


def chunk_pages(pages: list[str]) -> list[dict]:
    """Split each page's text into overlapping token chunks, tagged with page number (1-indexed)."""
    chunks: list[dict] = []
    chunk_size = settings.chunk_tokens
    overlap = settings.chunk_overlap_tokens

    for page_index, page_text in enumerate(pages):
        if not page_text:
            continue
        tokens = _encoder.encode(page_text)
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_text = _encoder.decode(tokens[start:end])
            chunks.append({"page": page_index + 1, "text": chunk_text})
            if end == len(tokens):
                break
            start = end - overlap

    return chunks
