import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.summarizer import router as summarizer_router
app = FastAPI(
    title="AWS Video Summarizer",
    description="Upload or link a video to get a transcript summary via AWS Transcribe + Bedrock Titan."
)
origins = [
    "http://localhost:3000",    # For React app
    "http://127.0.0.1:5500",    # For Live Server (VS Code)
    "http://localhost:5500",    # Alternate Live Server
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AWS Video Summarizer API"}
app.include_router(summarizer_router, prefix="/summarizer", tags=["summarizer"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    



