import json
from langchain_core.tools import tool

@tool
def fix_suggester_tool(error_info: str) -> str:
    """Given an error type and message, suggest likely causes and fixes."""
    error = json.loads(error_info)
    error_type = error.get("errorType", "")
    message = error.get("message", "")

    suggestions = {
        "ZeroDivisionError": {
            "summary": "You're trying to divide a number by zero.",
            "codeExample": "def divide(a, b):\n    if b == 0:\n        return 'Cannot divide by zero'\n    return a / b",
            "references": [
                "https://docs.python.org/3/library/exceptions.html#ZeroDivisionError"
            ]
        },
        "KeyError": {
            "summary": "You're trying to access a key that doesn't exist in a dictionary.",
            "codeExample": "value = my_dict.get('key', 'default')",
            "references": [
                "https://docs.python.org/3/library/exceptions.html#KeyError"
            ]
        },
        "IndexError": {
            "summary": "You're trying to access an index that is out of range.",
            "codeExample": "if i < len(my_list):\n    print(my_list[i])",
            "references": [
                "https://docs.python.org/3/library/exceptions.html#IndexError"
            ]
        }
    }

    default_fix = {
        "summary": f"No fix suggestion found for {error_type}.",
        "codeExample": "# Add input validation or debug this section.",
        "references": ["https://docs.python.org/3/library/exceptions.html"]
    }

    fix = suggestions.get(error_type, default_fix)
    return json.dumps(fix)