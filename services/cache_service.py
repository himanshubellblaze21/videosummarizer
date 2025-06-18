import hashlib
import json
import boto3
from core.config import AWS_REGION, S3_BUCKET
from services.summarizer_service import process_video

# Initialize S3 client
s3 = boto3.client("s3", region_name=AWS_REGION)


def compute_file_hash(path: str, chunk_size: int = 8192) -> str:
    """
    Compute MD5 hash of a file for caching lookup.
    """
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


async def summarize_with_cache(local_video_path: str) -> dict:
    """
    Check S3 for a cached summary. If not found, process the video and cache the result.

    Returns a dict: {"summary": str, "duration_seconds": float}
    """
    # 1) Fingerprint
    file_hash = compute_file_hash(local_video_path)
    summary_key = f"summaries/{file_hash}.json"

    # 2) Check cache
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=summary_key)
        payload = json.loads(obj['Body'].read())
        return payload
    except s3.exceptions.NoSuchKey:
        pass  # Cache miss

    # 3) Cache miss: process the video
    video_summary = await process_video(local_video_path)

    # 4) Store result
    cache_payload = {
        "summary": video_summary.text,
        "duration_seconds": video_summary.duration_seconds
    }
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=summary_key,
        Body=json.dumps(cache_payload),
        ContentType="application/json"
    )

    return cache_payload
