import json
import os
import logging
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_core.runnables import RunnableLambda
from trace_parser import trace_parser_tool, error_classifier_tool, is_valid_trace
from retriever_tool import retrieve_similar_traces
from fix_suggester_tool import fix_suggester_tool
from dotenv import load_dotenv
import ssl
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
LOG_PATH = "logs/trace_log.jsonl"

mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db = None
mongo_collection = None
mongo_available = False

try:
    os.makedirs("logs", exist_ok=True)
    logger.info("Log directory ensured")
except Exception as e:
    logger.error(f"Failed to create logs directory: {e}")
    raise

async def init_mongodb_connection():
    global mongo_client, mongo_db, mongo_collection, mongo_available
    
    if not MONGO_URI:
        logger.warning("MONGO_URI environment variable not set - MongoDB logging disabled")
        mongo_available = False
        return
    
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        mongo_client = AsyncIOMotorClient(
            MONGO_URI,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            ssl=True,
            retryWrites=True,
            w='majority'
        )
        
        await mongo_client.admin.command('ping')
        
        mongo_db = mongo_client["stacktrace-analyzer"]  
        mongo_collection = mongo_db["traces"]
        mongo_available = True
        logger.info("MongoDB connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.info("MongoDB logging disabled - service will continue with file logging only")
        mongo_available = False
        mongo_client = None
        mongo_db = None
        mongo_collection = None

async def check_mongodb_health():
    global mongo_available
    
    if not mongo_client:
        return False
        
    try:
        await mongo_client.admin.command('ping')
        if not mongo_available:
            logger.info("MongoDB connection restored")
            mongo_available = True
        return True
    except Exception as e:
        if mongo_available:
            logger.warning(f"MongoDB connection lost: {e}")
            mongo_available = False
        return False

async def log_trace(trace: str, result: dict):
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace": trace.strip(),
            "result": result
        }
        
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.debug("Trace logged to file successfully")
        
        if mongo_available and mongo_collection:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await mongo_collection.insert_one(entry)
                    logger.debug("Trace logged to MongoDB successfully")
                    break
                except Exception as mongo_error:
                    if attempt == max_retries - 1:
                        logger.warning(f"Failed to log to MongoDB after {max_retries} attempts: {mongo_error}")
                        await check_mongodb_health()
                    else:
                        await asyncio.sleep(0.5 * (attempt + 1))
        elif not mongo_available:
            logger.debug("MongoDB unavailable - logged to file only")
        
    except Exception as e:
        logger.error(f"Failed to log trace: {e}")
        logger.debug(f"Trace content: {trace[:100]}..." if len(trace) > 100 else trace)

async def analyze_trace(trace: str) -> dict:
    try:
        if mongo_client is None:
            await init_mongodb_connection()
            
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
        
        tasks = []
        
        async def parse_trace_async():
            try:
                parsed_frames_json = await asyncio.to_thread(trace_parser_tool.invoke, trace)
                parsed_frames = json.loads(parsed_frames_json)
                logger.debug("Trace parsing completed successfully")
                return parsed_frames
            except Exception as e:
                logger.error(f"Failed to parse trace: {e}")
                return []

        async def classify_error_async():
            try:
                error_info_json = await asyncio.to_thread(error_classifier_tool.invoke, trace)
                error_info = json.loads(error_info_json)
                logger.debug("Error classification completed successfully")
                return error_info
            except Exception as e:
                logger.error(f"Failed to classify error: {e}")
                return {"errorType": "Unknown", "message": "Failed to classify error"}

        async def retrieve_similar_async():
            try:
                similar_errors = await asyncio.to_thread(retrieve_similar_traces.invoke, trace)
                logger.debug(f"Found {len(similar_errors)} similar traces")
                return similar_errors
            except Exception as e:
                logger.error(f"Failed to retrieve similar traces: {e}")
                return []

        parsed_frames, error_info, similar_errors = await asyncio.gather(
            parse_trace_async(),
            classify_error_async(),
            retrieve_similar_async(),
            return_exceptions=True
        )

        if isinstance(parsed_frames, Exception):
            logger.error(f"Parse trace task failed: {parsed_frames}")
            parsed_frames = []
        
        if isinstance(error_info, Exception):
            logger.error(f"Error classification task failed: {error_info}")
            error_info = {"errorType": "Unknown", "message": "Failed to classify error"}
            
        if isinstance(similar_errors, Exception):
            logger.error(f"Similar traces task failed: {similar_errors}")
            similar_errors = []

        try:
            fix_input = {
                "error": error_info,
                "relatedErrors": similar_errors
            }
            fix_json = await asyncio.to_thread(fix_suggester_tool.invoke, json.dumps(fix_input))
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

        await log_trace(trace, result)
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

async def main():
    try:
        sample_trace = """
        Traceback (most recent call last):
          File "main.py", line 10, in <module>
            result = divide(5, 0)
          File "main.py", line 6, in divide
            return a / b
        ZeroDivisionError: division by zero
        """

        logger.info("Running async pipeline with sample trace")
        output = await analyze_trace(sample_trace)
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())