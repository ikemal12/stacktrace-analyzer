from sentence_transformers import SentenceTransformer
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

def create_index(traces: list[str]):
    first_vector = embed_trace(traces[0])
    d = first_vector.shape[0]
    index = faiss.IndexFlatL2(d)
    vectors = [first_vector] + [embed_trace(trace) for trace in traces[1:]]

    with open(METADATA_PATH, 'wb') as f:
        pickle.dump(traces, f)

    faiss.write_index(index, INDEX_PATH)
    print("Index created and saved.")

def load_index():
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata

def search_similar_traces(query: str, k: int = 3):
    index, metadata = load_index()
    query_vector = embed_trace(query).reshape(1, -1)
    distances, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata):
            results.append(metadata[idx])
    return results


if __name__ == "__main__":
    example_traces = [
        """Traceback (most recent call last):
           File "a.py", line 5, in <module>
             x = mylist[10]
         IndexError: list index out of range""",

        """Traceback (most recent call last):
           File "b.py", line 12, in <module>
             d = {'a': 1}
             print(d['z'])
         KeyError: 'z'""",

        """Traceback (most recent call last):
           File "c.py", line 8, in <module>
             result = divide(5, 0)
           File "c.py", line 3, in divide
             return a / b
         ZeroDivisionError: division by zero"""
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
    