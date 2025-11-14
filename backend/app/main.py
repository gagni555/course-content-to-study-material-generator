from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.v1.endpoints import documents, auth
from app.utils.monitoring import monitoring_service, RequestLoggingMiddleware

app = FastAPI(
    title="Course-Content-to-Study-Guide Generator API",
    description="Transform lecture materials into comprehensive study guides with AI-powered content analysis, practice questions, and concept maps",
    version="0.1.0"
)

# Add monitoring middleware first
request_middleware = RequestLoggingMiddleware(monitoring_service)
app.middleware("http")(request_middleware.log_request)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])

@app.get("/")
async def root():
    return {"message": "Course-Content-to-Study-Guide Generator API"}

@app.get("/health")
async def health_check():
    metrics = monitoring_service.get_current_metrics()
    return {
        "status": "healthy",
        "metrics": metrics
    }

@app.get("/metrics")
async def get_metrics():
    """Get current application metrics"""
    return monitoring_service.get_current_metrics()

@app.get("/metrics/history")
async def get_metrics_history(minutes: int = 60):
    """Get metrics history"""
    history = monitoring_service.get_metrics_history(minutes)
    return {"history": [m.dict() for m in history]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)