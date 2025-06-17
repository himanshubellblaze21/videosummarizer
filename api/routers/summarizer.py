from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app.services.video_io import save_upload, download_video
from app.services.cache_service import summarize_with_cache

router = APIRouter()

class URLRequest(BaseModel):
    video_url: HttpUrl = Field(..., alias="url")
    class Config:
        # allow both "url" and "video_url" in payload
        validate_by_name = True  # renamed in pydantic v2

@router.post("/upload")
async def summarize_upload(file: UploadFile = File(...)):
    path = await save_upload(file)

    result = await summarize_with_cache(path)
    return {"summary": result["summary"], "duration": result["duration_seconds"]}

@router.post("/url")
async def summarize_url(req: URLRequest):
    video_url = str(req.video_url)
    print("url received video_url:", video_url)
    try:
        path = await download_video(video_url)
    except Exception as e:
        print("download_video error:", e)
        raise HTTPException(status_code=400, detail=f"Download failed: {e}")

    try:

        result = await summarize_with_cache(path)
        return {"summary": result["summary"], "duration": result["duration_seconds"]}
    except Exception as e:
        print("summarize_with_cache error:", e)
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    





