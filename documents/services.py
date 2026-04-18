import os
from pathlib import Path
from .parser import parse_file
from .chunking import chunk_text, chunk_csv
from rag.embeddings import embed_texts
from rag.sparse import build_sparse_index
from rag.indexing import create_collection, upload_vectors
from llm.gemini import summarize_text

import fitz
from pathlib import Path
from google.oauth2 import service_account
from google.cloud import vision
from django.conf import settings


# Supported image extensions for Vision AI OCR
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


def get_vision_client():
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return vision.ImageAnnotatorClient(credentials=credentials)


def is_scanned_pdf(file_path: str, text_threshold: int = 50) -> bool:
    doc = fitz.open(file_path)
    total_text = "".join(page.get_text() for page in doc)
    doc.close()
    return len(total_text.strip()) < text_threshold


def extract_text_from_image(file_path: str) -> str:
    """
    Sends a single image file to Vision AI for OCR.
    """
    client = get_vision_client()

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    image = vision.Image(content=img_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision AI error: {response.error.message}")

    return response.full_text_annotation.text


def extract_text_via_vertex_vision(file_path: str) -> str:
    """
    Rasterizes each PDF page and sends to Vision AI for OCR.
    """
    client = get_vision_client()
    doc = fitz.open(file_path)
    full_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        image = vision.Image(content=img_bytes)
        response = client.document_text_detection(image=image)

        if response.error.message:
            raise RuntimeError(
                f"Vision AI error on page {page_num + 1}: {response.error.message}"
            )

        full_text.append(response.full_text_annotation.text)

    doc.close()
    return "\n".join(full_text)


def process_document(document):
    file_path = document.file.path
    ext = Path(file_path).suffix.lower()

    # 1. Parse + Chunk
    if ext == ".csv":
        chunks = chunk_csv(file_path)
        text = "\n".join(chunks)

    elif ext in IMAGE_EXTENSIONS:
        # ── Image file (jpg, png, tiff, etc.) → Vision AI OCR ──
        text = extract_text_from_image(file_path)
        chunks = chunk_text(text)

    elif ext == ".pdf" and is_scanned_pdf(file_path):
        # ── Scanned / image-based PDF → Vision AI OCR ──
        text = extract_text_via_vertex_vision(file_path)
        chunks = chunk_text(text)

    else:
        text = parse_file(file_path)
        chunks = chunk_text(text)

    # 2. Summarize
    summary = summarize_text(text)
    document.summary = summary
    document.save()

    # 3. Create Qdrant Collection
    collection_name = create_collection()
    document.qdrant_collection = collection_name
    document.save()

    # 4. Dense embeddings
    vectors = embed_texts(chunks)

    # 5. Upload dense vectors
    upload_vectors(collection_name, chunks, vectors)

    # 6. Build sparse index
    sparse_path = file_path + "_tfidf.pkl"
    build_sparse_index(chunks, sparse_path)

    return True