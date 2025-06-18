#for extract text from videos with simple upload 

import os
import json
import time
import uuid
import requests 
import boto3
import time 

from utils.ai_client import generate_text
from core.config import AWS_REGION, S3_BUCKET, TRANSCRIBE_LANGUAGE_CODE

# AWS clients
transcribe_client = boto3.client('transcribe', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)


class VideoSummary:
    def __init__(self, text: str, duration_seconds: float = None):
        self.text = text
        self.duration_seconds = duration_seconds


async def process_video(path: str) -> VideoSummary:
    """
    Orchestrates transcription via AWS Transcribe and summarization via Amazon Bedrock.
    """
    # 1. Upload local video to S3 for transcription
    suffix = os.path.splitext(path)[1]
    key = f"videos/{uuid.uuid4()}{suffix}"
    upload_start = time.time()
    s3_client.upload_file(path, S3_BUCKET, key)
    upload_end = time.time()
    print(f"[UPLOAD DEBUG] Upload time: {upload_end - upload_start:.2f} seconds")
    
    s3_uri = f"s3://{S3_BUCKET}/{key}"

    # 2. Start transcription job
    job_name = f"transcribe-{uuid.uuid4()}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode=TRANSCRIBE_LANGUAGE_CODE,
        Media={"MediaFileUri": s3_uri}
    )

    # 3. Poll until completion
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        st = status['TranscriptionJob']['TranscriptionJobStatus']
        if st in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)
    if st == 'FAILED':
        raise Exception(f"Transcription job {job_name} failed")

    # 4. Fetch transcript
    transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
    transcript_json = requests.get(transcript_uri).json()
    text = transcript_json['results']['transcripts'][0]['transcript']

    print(f"[TRANSCRIPT DEBUG] Transcript Text:\n{text}\n")

    # 5. Generate summary via Bedrock Titan
    # prompt = f"Summarize the following transcript:\n\n{text}"

    prompt = f"""
Summarize the following transcript in one concise paragraph. Provide only the summary—do not include timestamps.

Transcript:


{text}
"""
 
    summary_text = generate_text(prompt, max_tokens=500)

    print(f"[SUMMARY DEBUG] Summary Text:\n{summary_text}\n")
    return VideoSummary(text=summary_text)



























