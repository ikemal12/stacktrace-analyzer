import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import analyze_trace

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TraceRequest(BaseModel):
    trace: str

class TraceResponse(BaseModel):
    parsedTrace: list
    error: dict
    relatedErrors: list
    fixSuggestion: dict

app = FastAPI(title="Stacktrace Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "stacktrace-analyzer"}

@app.post("/analyze", response_model=TraceResponse)
async def analyze_endpoint(request: TraceRequest):
    try:
        trace = request.trace
        logger.info(f"REST analyze request received for trace of length {len(trace)}")
        
        if not trace or not trace.strip():
            raise HTTPException(status_code=400, detail="No trace provided")
        
        result = await analyze_trace(trace)
        logger.info("REST analyze request completed successfully")
        return TraceResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in REST analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Stacktrace Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    import uvicorn
    try:
        logger.info("Starting FastAPI server")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
