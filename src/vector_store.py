from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
import faiss
import numpy as np
import os
import pickle
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "faiss_index.index")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "data", "metadata.pkl")

try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("SentenceTransformer model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    raise

try:
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    logger.info(f"Data directory ensured at: {os.path.dirname(INDEX_PATH)}")
except Exception as e:
    logger.error(f"Failed to create data directory: {e}")
    raise

def embed_trace(trace: str) -> np.ndarray:
    try:
        if not trace or not trace.strip():
            logger.warning("Empty or whitespace-only trace provided for embedding")
            return np.zeros(384, dtype="float32")
        
        embedding = model.encode([trace])[0]
        result = np.array(embedding, dtype="float32")
        logger.debug(f"Successfully embedded trace of length {len(trace)} chars")
        return result
    except Exception as e:
        logger.error(f"Failed to embed trace: {e}")
        raise

def create_index(traces: list[dict]):
    try:
        logger.info(f"Starting index creation with {len(traces)} traces")
        
        if not traces:
            raise ValueError("Cannot create index from empty traces list")
        
        vectors = []
        skipped_count = 0
        
        for i, item in enumerate(traces):
            try:
                trace_text = item.get("trace", "")
                if trace_text and trace_text.strip():
                    vector = embed_trace(trace_text)
                    vectors.append(vector)
                else:
                    logger.warning(f"Skipping trace {i}: empty or missing trace text")
                    skipped_count += 1
            except Exception as e:
                logger.warning(f"Skipping trace {i} due to embedding error: {e}")
                skipped_count += 1
                continue

        if not vectors:
            raise ValueError("No valid trace vectors to index after processing all traces")

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} traces due to errors or empty content")

        d = vectors[0].shape[0]
        index = faiss.IndexFlatL2(d)
        index.add(np.stack(vectors))  # type: ignore
        logger.info(f"Created FAISS index with {len(vectors)} vectors, dimension {d}")

        with open(METADATA_PATH, 'wb') as f:
            pickle.dump(traces, f)
        logger.info(f"Saved metadata to {METADATA_PATH}")

        faiss.write_index(index, INDEX_PATH)
        logger.info(f"Saved FAISS index to {INDEX_PATH}")
        
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise

def load_index():
    try:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"Index file not found: {INDEX_PATH}")
        if not os.path.exists(METADATA_PATH):
            raise FileNotFoundError(f"Metadata file not found: {METADATA_PATH}")
            
        index = faiss.read_index(INDEX_PATH)
        logger.debug(f"Loaded FAISS index from {INDEX_PATH}")
        
        with open(METADATA_PATH, 'rb') as f:
            metadata = pickle.load(f)
        logger.debug(f"Loaded metadata with {len(metadata)} entries from {METADATA_PATH}")
        
        return index, metadata
        
    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        raise

def search_similar_traces(query: str, k: int = 3) -> list[Document]:
    try:
        logger.debug(f"Searching for {k} similar traces for query of length {len(query)}")
        
        if not query or not query.strip():
            logger.warning("Empty query provided for similarity search")
            return []
        
        index, metadata = load_index()
        
        query_vector = embed_trace(query).reshape(1, -1)
        
        k = min(k, index.ntotal)
        if k == 0:
            logger.warning("No traces in index to search")
            return []
        
        distances, indices = index.search(query_vector, k)
        logger.debug(f"Search completed, found indices: {indices[0]}")

        results = []
        for idx in indices[0]:
            try:
                if 0 <= idx < len(metadata):
                    trace = metadata[idx]
                    doc = Document(
                        page_content=trace.get("trace", str(trace)),
                        metadata={
                            "source": trace.get("source", "user_past_error"),
                            "url": trace.get("url", "")
                        }
                    )
                    results.append(doc)
                else:
                    logger.warning(f"Index {idx} out of range for metadata (length: {len(metadata)})")
            except Exception as e:
                logger.warning(f"Error processing result at index {idx}: {e}")
                continue
        
        logger.info(f"Found {len(results)} similar traces for query")
        return results
        
    except Exception as e:
        logger.error(f"Failed to search similar traces: {e}")
        return []


if __name__ == "__main__":
    try:
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

        logger.info("Creating index with example traces")
        create_index(example_traces)

        query = """Traceback (most recent call last):
                   File "main.py", line 10, in <module>
                     result = divide(4, 0)
                   File "main.py", line 6, in divide
                     return a / b
                 ZeroDivisionError: division by zero"""

        logger.info("Searching for similar traces")
        results = search_similar_traces(query)
        print("Top matches:")
        for i, result in enumerate(results):
            print(f"{i+1}. {result.page_content[:100]}...")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise
    