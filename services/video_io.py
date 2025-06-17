import os
import uuid
import tempfile
import requests
import aiofiles
from urllib.parse import urlparse, parse_qs, urlunparse
from pytube import YouTube
from fastapi import HTTPException
from yt_dlp import YoutubeDL

 
from app.core.config import S3_BUCKET, AWS_REGION
import boto3

s3_client = boto3.client("s3", region_name=AWS_REGION)


async def save_upload(file) -> str:
    """
    Save uploaded file locally and upload to S3.
    Returns local path for downstream processing.
    """
    suffix   = os.path.splitext(file.filename)[1]
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)

    local_path = os.path.join(temp_dir, f"{uuid.uuid4()}{suffix}")
    print("Saving file to local temp:", local_path)

    async with aiofiles.open(local_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    key = f"videos/{uuid.uuid4()}{suffix}"
    print("Uploading to S3:", key)
    s3_client.upload_file(local_path, S3_BUCKET, key)

    return local_path

def normalize_youtube_url(url: str) -> str:
    parsed   = urlparse(url)
    params   = parse_qs(parsed.query)
    video_id = params.get("v", [None])[0]
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL: missing v parameter")
    # rebuild URL so it’s just “?v=VIDEO_ID”
    clean = parsed._replace(query=f"v={video_id}", path="/watch")
    return urlunparse(clean)


async def download_with_ytdlp(url: str, tmp_dir: str) -> str:
    """
    Download any video URL (YouTube or otherwise) using yt-dlp,
    saving the best MP4 to tmp_dir.
    """
    # build an output template so we know the filename
    outtmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        
        # best single-file mp4; avoids needing ffmpeg to merge
        "format": "best[ext=mp4]",
        "outtmpl": outtmpl,
        "quiet":   True,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id")
        ext      = info.get("ext")
        if not video_id or not ext:
            raise HTTPException(status_code=400, detail="yt-dlp failed to extract video info")

        local_path = os.path.join(tmp_dir, f"{video_id}.{ext}")
        if not os.path.exists(local_path):
            raise HTTPException(status_code=500, detail="Downloaded file not found after yt-dlp run")
        return local_path


async def download_video(url: str) -> str:
    tmp_dir = tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)
    print("→ Using temp dir:", tmp_dir)
    print("→ download_video() called with URL:", url)

    # 1) If it’s a YouTube/watch or youtu.be link, use yt-dlp
    if "youtube.com/watch" in url or "youtu.be/" in url:
        local_path = await download_with_ytdlp(url, tmp_dir)

    else:
        # 2) Generic HTTP GET path (exactly as before)…
        resp = requests.get(url, stream=True, timeout=60)
        if resp.status_code != 200:
            raise HTTPException(status_code=400,
                                detail=f"Failed to download video: HTTP {resp.status_code}")
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("video/"):
            raise HTTPException(status_code=400,
                                detail=f"URL did not return a video (Content-Type={content_type})")
        suffix     = os.path.splitext(urlparse(url).path)[1] or ".mp4"
        filename   = f"{uuid.uuid4()}{suffix}"
        local_path = os.path.join(tmp_dir, filename)
        print("→ Writing to local file:", local_path)
        with open(local_path, "wb") as out:
            for chunk in resp.iter_content(chunk_size=8192):
                out.write(chunk)

    # 3) Upload to S3 (same as before)…
    suffix = os.path.splitext(local_path)[1]
    key    = f"videos/{uuid.uuid4()}{suffix}"
    print(f"→ Uploading to S3: bucket={S3_BUCKET}, key={key}")
    s3_client.upload_file(local_path, S3_BUCKET, key)
    print("→ Upload successful, returning local_path")
    return local_path



