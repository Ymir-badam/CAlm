import pickle
from sklearn.feature_extraction.text import TfidfVectorizer

def build_sparse_index(chunks, save_path):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(chunks)

    with open(save_path, "wb") as f:
        pickle.dump((vectorizer, tfidf_matrix), f)

    return True