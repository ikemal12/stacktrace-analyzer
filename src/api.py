import graphene
import logging
import asyncio
from graphene import ObjectType, String, Int, List, Field
from pipeline import analyze_trace

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Source(graphene.ObjectType):
    snippet = String()
    sourceType = String()
    url = String()

class TraceLine(graphene.ObjectType):
    file = String()
    line = Int()
    function = String()
    code = String()

class Error(graphene.ObjectType):
    errorType = String()
    message = String()

class FixSuggestion(graphene.ObjectType):
    summary = String()
    codeExample = String()
    references = List(Source)

class AnalyzeResult(graphene.ObjectType):
    parsedTrace = List(TraceLine)
    error = Field(Error)
    relatedErrors = List(String)
    fixSuggestion = Field(FixSuggestion)

class Query(ObjectType):
    analyze = Field(AnalyzeResult, trace=String(required=True))

    async def resolve_analyze(self, info, trace):
        try:
            logger.info(f"GraphQL analyze request received for trace of length {len(trace)}")
            
            if not trace or not trace.strip():
                logger.warning("Empty trace provided to GraphQL API")
                return {
                    "parsedTrace": [],
                    "error": {"errorType": "EmptyTrace", "message": "No trace provided"},
                    "relatedErrors": [],
                    "fixSuggestion": {"summary": "", "codeExample": "", "references": []}
                }
            
            result = await analyze_trace(trace)
            logger.info("GraphQL analyze request completed successfully")
            return {
                "parsedTrace": result["parsedTrace"],
                "error": result["error"],
                "relatedErrors": result["relatedErrors"],
                "fixSuggestion": result["fixSuggestion"]
            }
            
        except Exception as e:
            logger.error(f"Error in GraphQL resolve_analyze: {e}")
            return {
                "parsedTrace": [],
                "error": {"errorType": "SystemError", "message": f"Server error: {str(e)}"},
                "relatedErrors": [],
                "fixSuggestion": {"summary": "Server error occurred", "codeExample": "", "references": []}
            }

schema = graphene.Schema(query=Query)