from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
import faiss
import numpy as np
import os
import pickle

model = SentenceTransformer('all-MiniLM-L6-v2')

INDEX_PATH = "data/faiss_index.index"
METADATA_PATH = "data/metadata.pkl"

os.makedirs("data", exist_ok=True)

def embed_trace(trace: str) -> np.ndarray:
    embedding = model.encode([trace])[0]
    return np.array(embedding, dtype="float32")

def create_index(traces: list[dict]):
    vectors = []
    for item in traces:
        trace_text = item.get("trace", "")
        if trace_text.strip():
            vector = embed_trace(trace_text)
            vectors.append(vector)

    if not vectors:
        raise ValueError("No valid trace vectors to index.")

    d = vectors[0].shape[0]
    index = faiss.IndexFlatL2(d)
    index.add(np.stack(vectors)) # type: ignore

    with open(METADATA_PATH, 'wb') as f:
        pickle.dump(traces, f)

    faiss.write_index(index, INDEX_PATH)
    print("Index created and saved.")

def load_index():
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata

def search_similar_traces(query: str, k: int = 3) -> list[Document]:
    index, metadata = load_index()
    query_vector = embed_trace(query).reshape(1, -1)
    distances, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata):
            trace = metadata[idx]
            doc = Document(
                page_content=trace.get("trace", trace),
                metadata={
                    "source":trace.get("source", "user_past_error"),
                    "url": trace.get("url", "")
                }
            )
            results.append(doc)
    return results


if __name__ == "__main__":
    example_traces = [
        {
            "trace": """Traceback (most recent call last):
    File "main.py", line 10, in <module>
        result = divide(5, 0)
    File "main.py", line 6, in divide
        return a / b
    ZeroDivisionError: division by zero""",
            "source": "python_docs",
            "url": "https://docs.python.org/3/library/exceptions.html#ZeroDivisionError"
        },
        {
            "trace": """Traceback (most recent call last):
    File "main.py", line 12, in <module>
        item = my_list[10]
    IndexError: list index out of range""",
            "source": "user_past_error",
            "url": ""
        },
        {
            "trace": """Traceback (most recent call last):
    File "main.py", line 8, in <module>
        value = d['missing']
    KeyError: 'missing'""",
            "source": "python_docs",
            "url": "https://docs.python.org/3/library/exceptions.html#KeyError"
        }
    ]


    create_index(example_traces)

    query = """Traceback (most recent call last):
               File "main.py", line 10, in <module>
                 result = divide(4, 0)
               File "main.py", line 6, in divide
                 return a / b
             ZeroDivisionError: division by zero"""

    print("Top matches:")
    print(search_similar_traces(query))
    