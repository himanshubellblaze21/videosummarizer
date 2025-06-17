import os
import json
import boto3
from botocore.config import Config
from app.core.config import AWS_REGION, BEDROCK_MODEL_ID

# Initialize Bedrock runtime client
client = boto3.client(
    'bedrock-runtime',
    region_name=AWS_REGION,
    config=Config()
)

def generate_text(prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    payload = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": max_tokens,
            "temperature": temperature,
            "topP": 1,
            "stopSequences": []
        }
    }
    response = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    result = json.loads(response['body'].read())
    return result["results"][0]["outputText"].strip()

