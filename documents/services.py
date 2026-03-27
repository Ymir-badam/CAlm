import os
from pathlib import Path
from .parser import parse_file
from .chunking import chunk_text, chunk_csv
from rag.embeddings import embed_texts
from rag.sparse import build_sparse_index
from rag.indexing import create_collection, upload_vectors
from llm.gemini import summarize_text

def process_document(document):

    file_path = document.file.path
    ext = Path(file_path).suffix.lower()

    # 1. Parse + Chunk (CSV gets special row-per-chunk treatment)
    if ext == ".csv":
        chunks = chunk_csv(file_path)
        text = "\n".join(chunks)  # flat text just for summarization
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