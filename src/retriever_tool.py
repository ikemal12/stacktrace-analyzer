from langchain_core.tools import tool
from vector_store import search_similar_traces

@tool
def retrieve_similar_traces(trace: str) -> list[dict]:
    """Given a stack trace, return a list of similar past traces and their metadata."""
    docs = search_similar_traces(trace)
    return [
        {
            "snippet": doc.page_content,
            "sourceType": doc.metadata.get("source", ""),
            "url": doc.metadata.get("url", ""),
        }
        for doc in docs
    ]


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
