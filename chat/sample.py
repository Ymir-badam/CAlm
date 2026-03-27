import os
import google.generativeai as genai
genai.configure(api_key="AIzaSyDXIJUwdo4LRRiZ8esmDXgGcvBatcorrYw")

# model = genai.GenerativeModel("gemini-2.5-flash")
model = genai.GenerativeModel("gemini-2.5-flash-lite")
llm =genai.GenerativeModel("gemini-2.5-flash-lite")

query=""
prompt = f"""classify the query : {query}
 into one of the following categories:
1 Non RAG if it can be answered without referring to the document
2 RAG if it requires retrieval of specific information from the document
3 FULL SCAN if it asks for analysis, conclusions, or insights based on the entire document 
4 UNKNOWN if it cannot be classified into the above categories
5 EMPTY if the query is empty or contains only whitespace
Provide only the category name as the answer.

"""
# response=model.generate_content(prompt)
# print(response.text)

import os
from qdrant_client import QdrantClient

client = QdrantClient(
    url=os.getenv("http://localhost:6333"),
    api_key=os.getenv("xLwS6ibAXv1W5pG8UmRmPBfrQCRla9tq"),
    timeout=60.0 ,
)
def full_scan(document, query):
    collection_name = document#.qdrant_collection
    
    # 1. Fetch all chunks using scroll
    points, _ = client.scroll(
        collection_name=collection_name,
        # scroll_filter={"must": [{"key": "doc_id", "match": {"value": document.id}}]},
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
    
full_scan("9980c87a-1f84-4d7a-a99d-cb62de626f0c", "Analyse the document and provide insights on its main themes and conclusions.")