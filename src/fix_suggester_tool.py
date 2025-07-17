import json
import logging
from langchain_core.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_ollama import ChatOllama
from tenacity import retry, stop_after_attempt, wait_fixed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    llm = ChatOllama(model="mistral", temperature=0.3)
    logger.info("ChatOllama model initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ChatOllama model: {e}")
    raise

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

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
def get_fix_from_llm(error_type: str, message: str, context: str) -> dict:
    """Invoke LLM with retry logic."""
    try:
        logger.debug(f"Requesting fix suggestion for error: {error_type}")
        chain = prompt | llm | parser
        result = chain.invoke({
            "errorType": error_type,
            "message": message,
            "context": context,
            "format_instructions": parser.get_format_instructions()
        })
        logger.debug("LLM fix suggestion generated successfully")
        return result
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        raise

@tool
def fix_suggester_tool(error_info: str) -> str:
    """Given an error type and message, suggest likely causes and fixes with references."""
    try:
        logger.debug("Processing fix suggestion request")
        
        if not error_info or not error_info.strip():
            logger.warning("Empty error_info provided to fix_suggester_tool")
            return json.dumps({
                "summary": "No error information provided.",
                "codeExample": "",
                "references": []
            })
        
        data = json.loads(error_info)
        error_type = data.get("error", {}).get("errorType", "")
        message = data.get("error", {}).get("message", "")
        sources = data.get("relatedErrors", [])

        if not error_type:
            logger.warning("No error type found in error_info")
            return json.dumps({
                "summary": "No error type specified.",
                "codeExample": "",
                "references": []
            })

        context = "\n\n".join(
            f"[{s.get('sourceType', '')}] {s.get('snippet', '')}" for s in sources
        )

        result = get_fix_from_llm(error_type, message, context)

        code = result.get("codeExample", "")
        if code.startswith("```"):
            code = code.strip("`\n")
            if code.startswith("python"):
                code = code[len("python"):].lstrip()
            result["codeExample"] = code

        logger.info(f"Fix suggestion generated for error type: {error_type}")
        return json.dumps(result)
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in error_info: {e}")
        return json.dumps({
            "summary": "Invalid error information format.",
            "codeExample": "",
            "references": [],
            "error": "JSON decode error"
        })
    except Exception as e:
        logger.error(f"Unexpected error in fix_suggester_tool: {e}")
        return json.dumps({
            "summary": "An error occurred while processing the fix suggestion.",
            "codeExample": "",
            "references": [],
            "error": str(e)
        })
