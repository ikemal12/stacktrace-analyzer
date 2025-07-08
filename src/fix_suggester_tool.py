import json
from langchain_core.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.chat_models import ChatOllama

llm = ChatOllama(model="mistral", temperature=0.3)
parser = JsonOutputParser()

prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant that suggests causes and fixes for Python errors.

Here is the error type and message:
Error Type: {errorType}
Error Message: {message}

Here is some relevant context (examples and documentation):
{context}

Return *only* a valid JSON object in the following format (do NOT include any explanation, markdown, or backticks):

{{
  "summary": "...",
  "codeExample": "...",
  "references": [
    {{
      "snippet": "...",
      "sourceType": "...",
      "url": "..."
    }}
  ]
}}
""")


@tool
def fix_suggester_tool(error_info: str) -> str:
    """Given an error type and message, suggest likely causes and fixes with references."""
    try:
        data = json.loads(error_info)
        error_type = data.get("error", {}).get("errorType", "")
        message = data.get("error", {}).get("message", "")
        sources = data.get("relatedErrors", [])

        context = "\n\n".join(
            f"[{s.get('sourceType', '')}] {s.get('snippet', '')}" for s in sources
        )

        chain = prompt | llm | parser

        result = chain.invoke({
            "errorType": error_type,
            "message": message,
            "context": context,
            "format_instructions": parser.get_format_instructions()
        })

        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({
            "summary": "An error occurred while processing the fix suggestion.",
            "codeExample": "",
            "references": [],
            "error": str(e)
        })
