import uuid
from qdrant_client.models import VectorParams, Distance
from .qdrant_client import client

def create_collection():
    collection_name = str(uuid.uuid4())

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    return collection_name
def upload_vectors(collection_name, chunks, vectors):
    points = []

    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        points.append({
            "id": idx,
            "vector": vector,
            "payload": {
                "text": chunk
            }
        })

    client.upsert(collection_name=collection_name, points=points)