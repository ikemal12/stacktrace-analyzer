import os
from typing import Optional

class Config:
    PORT: int = int(os.getenv("PORT", "8001"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    MAX_TRACE_SIZE: int = int(os.getenv("MAX_TRACE_SIZE", "50000"))
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "1000000"))
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    MONGO_URI: Optional[str] = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    LOG_PATH: str = os.getenv("LOG_PATH", "logs/trace_log.jsonl")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    IS_PRODUCTION: bool = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RENDER") is not None

config = Config()
