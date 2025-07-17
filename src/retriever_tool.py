import logging
from langchain_core.tools import tool
from vector_store import search_similar_traces

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def retrieve_similar_traces(trace: str) -> list[dict]:
    """Given a stack trace, return a list of similar past traces and their metadata."""
    try:
        logger.debug(f"Retrieving similar traces for trace of length {len(trace)}")
        
        if not trace or not trace.strip():
            logger.warning("Empty trace provided to retrieve_similar_traces")
            return []
        
        docs = search_similar_traces(trace)
        results = [
            {
                "snippet": doc.page_content,
                "sourceType": doc.metadata.get("source", ""),
                "url": doc.metadata.get("url", ""),
            }
            for doc in docs
        ]
        
        logger.info(f"Retrieved {len(results)} similar traces")
        return results
        
    except Exception as e:
        logger.error(f"Failed to retrieve similar traces: {e}")
        return []


if __name__ == "__main__":
    query = """Traceback (most recent call last):
               File "main.py", line 10, in <module>
                 result = divide(4, 0)
               File "main.py", line 6, in divide
                 return a / b
             ZeroDivisionError: division by zero"""
    
    results = retrieve_similar_traces.invoke(query)
    print("Similar traces:")
    for r in results:
        print(r)
