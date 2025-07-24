from pipeline import analyze_trace, check_mongodb_health
from config import config
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import asyncio

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        self.clients[client_ip] = [req_time for req_time in self.clients[client_ip] if now - req_time < self.period]
        
        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        self.clients[client_ip].append(now)
        response = await call_next(request)
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_size:
                raise HTTPException(status_code=413, detail="Request too large")
        response = await call_next(request)
        return response

app = FastAPI(
    title="Stack Trace Analyzer API",
    description="AI-powered Python error analysis and fix suggestions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(RequestSizeLimitMiddleware, max_size=10*1024*1024)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

class StackTraceRequest(BaseModel):
    trace: str = Field(..., min_length=1, max_length=50000, description="The stack trace to analyze")

class AnalysisResponse(BaseModel):
    error_details: dict
    fix_suggestions: str
    parsed_trace: list
    related_errors: list
    analysis_timestamp: str
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_connected: bool
    version: str

@app.get("/", response_model=dict)
async def root():
    return {
        "message": "Stack Trace Analyzer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    db_status = await check_mongodb_health()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        database_connected=db_status,
        version="1.0.0"
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_stack_trace(request: StackTraceRequest):
    try:
        start_time = time.time()
        
        if not request.trace.strip():
            raise HTTPException(status_code=400, detail="Stack trace cannot be empty")
        
        result = await analyze_trace(request.trace)
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            error_details=result['error_details'],
            fix_suggestions=result['fix_suggestions'],
            parsed_trace=result['parsed_trace'],
            related_errors=result['related_errors'],
            analysis_timestamp=datetime.now().isoformat(),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing stack trace: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return Response(
        content='{"detail": "Not found"}',
        status_code=404,
        media_type="application/json"
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return Response(
        content='{"detail": "Internal server error"}',
        status_code=500,
        media_type="application/json"
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Stack Trace Analyzer API...")
    db_status = await check_mongodb_health()
    if db_status:
        logger.info("MongoDB connection established")
    else:
        logger.warning("MongoDB not available, using file-based fallback")
    logger.info("API server ready!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="localhost",
        port=8001,
        reload=True,
        log_level="info"
    )
