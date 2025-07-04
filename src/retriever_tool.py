from langchain_core.tools import tool
from vector_store import search_similar_traces

@tool
def retrieve_similar_traces(trace: str) -> list[str]:
    """Given a stack trace, return a list of similar past traces."""
    return search_similar_traces(trace)


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
