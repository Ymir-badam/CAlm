import re


def chunk_text(text, chunk_size=400, overlap=80):
    """
    chunk_size = approx number of words per chunk
    overlap = overlapping words between chunks
    """

    text = re.sub(r"\s+", " ", text).strip()

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        words = sentence.split()
        sentence_length = len(words)

        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))

            overlap_words = " ".join(current_chunk).split()[-overlap:]
            current_chunk = overlap_words.copy()
            current_length = len(current_chunk)

        current_chunk.extend(words)
        current_length += sentence_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
import csv

def chunk_csv(file_path):
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Each row becomes "Column: Value, Column: Value" — embeds well
            text = ", ".join(f"{k}: {v}" for k, v in row.items() if str(v).strip())
            if text:
                chunks.append(text)
    return chunks