import json
import os
import logging
from datetime import datetime, timezone
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from langchain_core.runnables import RunnableLambda
from trace_parser import trace_parser_tool, error_classifier_tool, is_valid_trace
from retriever_tool import retrieve_similar_traces
from fix_suggester_tool import fix_suggester_tool
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
LOG_PATH = "logs/trace_log.jsonl"

try:
    os.makedirs("logs", exist_ok=True)
    logger.info("Log directory ensured")
except Exception as e:
    logger.error(f"Failed to create logs directory: {e}")
    raise

try:
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable not set")
    mongo_client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    mongo_db = mongo_client["stacktrace-analyzer"]  
    mongo_collection = mongo_db["traces"]
    logger.info("MongoDB connection established")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

def log_trace(trace: str, result: dict):
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace": trace.strip(),
            "result": result
        }
        
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.debug("Trace logged to file successfully")
        
        mongo_collection.insert_one(entry)
        logger.debug("Trace logged to MongoDB successfully")
        
    except Exception as e:
        logger.error(f"Failed to log trace: {e}")
        logger.debug(f"Trace content: {trace[:100]}..." if len(trace) > 100 else trace)

def analyze_trace(trace: str) -> dict:
    """Analyzes a stack trace and returns frames and errors."""
    try:
        logger.info(f"Starting trace analysis for trace of length {len(trace)}")
        
        if not trace or not trace.strip():
            logger.warning("Empty trace provided for analysis")
            return {
                "parsedTrace": [],
                "error": {
                    "errorType": "EmptyTrace",
                    "message": "No trace content provided."
                },
                "relatedErrors": [],
                "fixSuggestion": {
                    "summary": "",
                    "codeExample": "",
                    "references": []
                }
            }
        
        if not is_valid_trace(trace):
            logger.warning("Invalid trace format detected")
            return {
                "parsedTrace": [],
                "error": {
                    "errorType": "InvalidTrace",
                    "message": "The input does not appear to be a valid Python traceback."
                },
                "relatedErrors": [],
                "fixSuggestion": {
                    "summary": "",
                    "codeExample": "",
                    "references": []
                }
            }
        
        try:
            parsed_frames_json = trace_parser_tool.invoke(trace)
            parsed_frames = json.loads(parsed_frames_json)
            logger.debug("Trace parsing completed successfully")
        except Exception as e:
            logger.error(f"Failed to parse trace: {e}")
            parsed_frames = []

        try:
            error_info_json = error_classifier_tool.invoke(trace)
            error_info = json.loads(error_info_json)
            logger.debug("Error classification completed successfully")
        except Exception as e:
            logger.error(f"Failed to classify error: {e}")
            error_info = {"errorType": "Unknown", "message": "Failed to classify error"}

        try:
            similar_errors = retrieve_similar_traces.invoke(trace)
            logger.debug(f"Found {len(similar_errors)} similar traces")
        except Exception as e:
            logger.error(f"Failed to retrieve similar traces: {e}")
            similar_errors = []

        try:
            fix_input = {
                "error": error_info,
                "relatedErrors": similar_errors
            }
            fix_json = fix_suggester_tool.invoke(json.dumps(fix_input))
            fix_info = json.loads(fix_json)
            logger.debug("Fix suggestion generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate fix suggestion: {e}")
            fix_info = {
                "summary": "An error occurred while generating fix suggestions.",
                "codeExample": "",
                "references": [],
                "error": str(e)
            }

        result = {
            "parsedTrace": parsed_frames,
            "error": error_info,
            "relatedErrors": similar_errors,
            "fixSuggestion": fix_info
        }

        log_trace(trace, result)
        logger.info("Trace analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_trace: {e}")
        return {
            "parsedTrace": [],
            "error": {
                "errorType": "SystemError",
                "message": f"An unexpected error occurred: {str(e)}"
            },
            "relatedErrors": [],
            "fixSuggestion": {
                "summary": "System error occurred during analysis.",
                "codeExample": "",
                "references": []
            }
        }

pipeline = RunnableLambda(analyze_trace)

if __name__ == "__main__":
    try:
        sample_trace = """
        Traceback (most recent call last):
          File "main.py", line 10, in <module>
            result = divide(5, 0)
          File "main.py", line 6, in divide
            return a / b
        ZeroDivisionError: division by zero
        """

        logger.info("Running pipeline with sample trace")
        output = pipeline.invoke(sample_trace)
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise