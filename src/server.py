import logging
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from pipeline import analyze_trace, check_mongodb_health
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from config import config

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = config.MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                return Response(
                    content="Request too large", 
                    status_code=413,
                    media_type="application/json"
                )
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = getattr(request.client, 'host', '127.0.0.1') if request.client else '127.0.0.1'
        current_time = time.time()
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            return Response(
                content="Rate limit exceeded. Try again later.",
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        self.requests[client_ip].append(current_time)
        return await call_next(request)

class TraceRequest(BaseModel):
    trace: str = Field(..., max_length=config.MAX_TRACE_SIZE, description="Stack trace to analyze")

class TraceResponse(BaseModel):
    parsedTrace: list
    error: dict
    relatedErrors: list
    fixSuggestion: dict

app = FastAPI(title="Stacktrace Analyzer API", version="1.0.0")

app.add_middleware(RequestSizeLimitMiddleware, max_size=config.MAX_REQUEST_SIZE)
app.add_middleware(RateLimitMiddleware, max_requests=config.MAX_REQUESTS_PER_MINUTE, window_seconds=config.RATE_LIMIT_WINDOW)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    try:
        health_status = {
            "status": "healthy",
            "service": "stacktrace-analyzer",
            "timestamp": str(asyncio.get_event_loop().time()),
            "dependencies": {
                "mongodb": await check_mongodb_health(),
                "filesystem": True
            }
        }
        
        if not health_status["dependencies"]["mongodb"]:
            health_status["status"] = "degraded"
            health_status["message"] = "MongoDB unavailable - using file logging only"
            
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "service": "stacktrace-analyzer",
            "error": str(e)
        }

def validate_stacktrace(trace: str) -> bool:
    if not trace or not trace.strip():
        return False
    
    trace_lower = trace.lower()
    required_indicators = ['traceback', 'error', 'exception', 'file', 'line']
    python_indicators = ['traceback (most recent call last)', '.py', 'error:', 'exception:']
    
    has_basic_structure = any(indicator in trace_lower for indicator in required_indicators)
    has_python_structure = any(indicator in trace_lower for indicator in python_indicators)
    
    if len(trace) > config.MAX_TRACE_SIZE:
        return False
    
    suspicious_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
    has_suspicious_content = any(pattern in trace_lower for pattern in suspicious_patterns)
    
    return (has_basic_structure or has_python_structure) and not has_suspicious_content

@app.post("/analyze", response_model=TraceResponse)
async def analyze_endpoint(request: TraceRequest):
    try:
        trace = request.trace.strip()
        logger.info(f"REST analyze request received for trace of length {len(trace)}")
        
        if not trace:
            raise HTTPException(status_code=400, detail="No trace provided")
        
        if not validate_stacktrace(trace):
            raise HTTPException(
                status_code=400, 
                detail="Invalid trace format. Please provide a valid Python stack trace."
            )
        
        if len(trace) > config.MAX_TRACE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Trace too long. Maximum size is {config.MAX_TRACE_SIZE} characters."
            )
        
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
        uvicorn.run(app, host=config.HOST, port=config.PORT, log_level=config.LOG_LEVEL.lower())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
