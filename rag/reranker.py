from sentence_transformers import CrossEncoder

reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
# reranker_model = "model"   
def rerank(query, texts):
    # print("Reranking with query:", query)
    # print("Original retrieved texts:", texts)
    pairs = [[query, text] for text in texts]
    scores = reranker_model.predict(pairs)

    scored = list(zip(texts, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    # print("Reranked results:", scored)

    return [text for text, _ in scored]