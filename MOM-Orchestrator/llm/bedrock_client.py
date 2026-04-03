"""
AWS Bedrock LLM Client — AgentMesh AI
Shared client used by all reasoning agents (intent_refiner, extractors, response_generator).
Reads credentials and model config from environment — never hardcoded.
"""
from __future__ import annotations
import json
import os
import boto3
from botocore.config import Config

_client = None


def get_bedrock_client():
    global _client
    if _client is None:
        _client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": 2},
            ),
        )
    return _client


async def invoke_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Invokes the configured Bedrock model and returns the text response.
    Uses the OpenAI-compatible converse API available on Bedrock.
    """
    import asyncio

    model_id = os.getenv("MODEL_ID", "openai.gpt-oss-120b-1:0")
    client = get_bedrock_client()

    messages = [{"role": "user", "content": user_prompt}]

    def _call():
        return client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[
                {"role": m["role"], "content": [{"text": m["content"]}]}
                for m in messages
            ],
            inferenceConfig={"maxTokens": 4096, "temperature": 0.2},
        )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, _call)

    # The model may return multiple content blocks (e.g. reasoning + text).
    # Find the first block that carries a plain "text" key.
    for block in response["output"]["message"]["content"]:
        if "text" in block:
            return block["text"]
    raise ValueError(f"No text block found in response content: {response['output']['message']['content']}")


async def invoke_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Calls the LLM and parses the response as JSON.
    Wraps the user prompt to enforce JSON output.
    """
    json_system = (
        system_prompt
        + "\n\nIMPORTANT: Respond ONLY with valid JSON. No explanation, no markdown fences."
    )
    raw = await invoke_llm(json_system, user_prompt)

    # Strip markdown fences if model adds them anyway
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
