import pickle
import os
import numpy as np
from qdrant_client.models import Filter
from .embeddings import embed_texts
from .qdrant_client import client


def dense_search(collection_name, query):
    query_vector = embed_texts(query)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=5,
    )

    return [
        {
            "text": point.payload["text"],
            "score": point.score,
            "document_id": point.payload.get("document_id"),
        }
        for point in results.points
    ]
def sparse_score(sparse_path, query, chunks):
    with open(sparse_path, "rb") as f:
        vectorizer, tfidf_matrix = pickle.load(f)

    query_vec = vectorizer.transform([query])
    scores = (tfidf_matrix @ query_vec.T).toarray().flatten()

    return list(zip(chunks, scores))
def hybrid_search(document, query):
    dense_results = dense_search(document.qdrant_collection, query)
    # sparse_results = sparse_score(document.qdrant_collection, query)

    if not dense_results:
        return []

    combined = []

    for i in range(len(dense_results)):
        dense = dense_results[i]
        # sparse = sparse_results[i]

        final_score = (0.7 * dense["score"])# + (0.3 * sparse["score"])

        combined.append({
            "text": dense["text"],
            "score": final_score,
            "doc_id": dense.get("document_id"),  # or dense["doc_id"]
            "doc_title": dense.get("title", "Unknown Document")
        })

    combined.sort(key=lambda x: x["score"], reverse=True)
    # print("Combined search results:", combined)

    return combined

import os
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# model = genai.GenerativeModel("gemini-2.5-flash")
model = genai.GenerativeModel("gemini-2.5-flash-lite")
def full_scan(document, query):
    collection_name = document.qdrant_collection
    
    # 1. Fetch all chunks using scroll
    points, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter={"must": [{"key": "doc_id", "match": {"value": document.id}}]},
        with_payload=True
    )
    
    individual_analyses = []

    # 2. Map Phase: Analyze each chunk one by one
    for p in points:
        chunk_text = p.payload['text']
        # Ask the LLM to extract only info relevant to the query from this specific chunk
        response = model.generate_content(f"Query: {query}. Analyze this specific snippet and extract key info: {chunk_text}")
        individual_analyses.append(response.text)
        print(chunk_text)
        print("#######################")
        print(response.text)

    # 3. Reduce Phase: Combine all mini-analyses into one final output
    combined_notes = "\n".join(individual_analyses)
    final_output = model.generate_content(
        f"Based on these individual analyses of document sections, "
        f"provide a final concise answer for: {query}\n\nAnalyses:\n{combined_notes}"
    )
    return final_output.text