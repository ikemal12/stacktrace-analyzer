import re
import json
from typing import List, Dict, Any
from langchain.tools import tool


def is_valid_trace(trace: str) -> bool:
    """Check if the input looks like a valid stack trace."""
    return (
        isinstance(trace, str)
        and "Traceback (most recent call last):" in trace
        and "File" in trace
        and "line" in trace
    )

def parse_trace(trace: str) -> List[Dict[str, Any]]:
    lines = trace.strip().split("\n")
    frames = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r'File "(.+?)", line (\d+), in (\S+)', line)

        if match:
            file, line_num, func = match.groups()
            code_line = lines[i+1].strip() if i+1 < len(lines) else ""
            frames.append({
                "file": file,
                "line": int(line_num),
                "function": func,
                "code": code_line
            })
            i += 2
        else:
            i += 1
        
    return frames


@tool
def trace_parser_tool(trace: str) -> str:
    """Parses the stack trace and returns it in JSON format."""
    parsed = parse_trace(trace)
    return json.dumps(parsed, indent=2)


def extract_error_info(trace: str) -> Dict[str, str]:
    lines = trace.strip().split("\n")

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*Error): (.+)', line)
        if match:
            error_type, message = match.groups()
            return {"errorType": error_type, "message": message}
        else:
            return {"errorType": "UnknownError", "message": line}
    
    return {"errorType": "UnknownError", "message": ""}


@tool
def error_classifier_tool(trace: str) -> str:
    "Retrieves error type and message from the stack trace."
    info = extract_error_info(trace)
    return json.dumps(info, indent=2)



if __name__ == "__main__":
    sample_trace = """
    Traceback (most recent call last):
      File "main.py", line 10, in <module>
        result = divide(5, 0)
      File "main.py", line 6, in divide
        return a / b
    ZeroDivisionError: division by zero
    """

    print(trace_parser_tool.invoke(sample_trace))
    print(error_classifier_tool.invoke(sample_trace))
