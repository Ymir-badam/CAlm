import csv
import PyPDF2
from docx import Document as DocxDocument

def parse_file(file_path):
    if file_path.endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text

    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif file_path.endswith(".docx"):
        doc = DocxDocument(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return ""
        # Convert to readable pipe-delimited text so the LLM understands structure
        header = " | ".join(rows[0])
        separator = "-" * len(header)
        body = "\n".join(" | ".join(row) for row in rows[1:])
        return f"{header}\n{separator}\n{body}"

    else:
        raise ValueError(f"Unsupported file format: {file_path.split('.')[-1]}")