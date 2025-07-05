import json
from langchain_core.runnables import RunnableLambda
from trace_parser import trace_parser_tool, error_classifier_tool
from retriever_tool import retrieve_similar_traces
from fix_suggester_tool import fix_suggester_tool

def analyze_trace(trace: str) -> dict:
    """Analyzes a stack trace and returns frames and errors."""
    parsed_frames_json = trace_parser_tool.invoke(trace)
    error_info_json = error_classifier_tool.invoke(trace)
    similar_errors = retrieve_similar_traces.invoke(trace)

    parsed_frames = json.loads(parsed_frames_json)
    error_info = json.loads(error_info_json)

    fix_input = {
        "error": error_info,
        "relatedErrors": similar_errors
    }

    fix_json = fix_suggester_tool.invoke(json.dumps(fix_input))
    fix_info = json.loads(fix_json)

    return {
        "parsedTrace": parsed_frames,
        "error": error_info,
        "relatedErrors": similar_errors,
        "fixSuggestion": fix_info
    }

pipeline = RunnableLambda(analyze_trace)

if __name__ == "__main__":
    sample_trace = """
    Traceback (most recent call last):
      File "main.py", line 10, in <module>
        result = divide(5, 0)
      File "main.py", line 6, in divide
        return a / b
    ZeroDivisionError: division by zero
    """

    output = pipeline.invoke(sample_trace)
    print(json.dumps(output, indent=2))