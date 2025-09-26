import os
import json
import re
import logging
import httpx
from utils.config import Config

ANTHROPIC_API_KEY = Config.CLAUDE_API_KEY

logger = logging.getLogger(__name__)

# Anthropic Messages API endpoint
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

def _extract_json_from_text(text: str):
    """Extract JSON from Claude's text response."""
    if not text:
        raise ValueError("Empty text")

    # Remove markdown code blocks
    text = re.sub(r'```json\s*|\s*```', '', text).strip()

    # Try to find JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback to full text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON from text: {e}")

async def call_claude_raw(prompt: str, model: str = "claude-3-5-sonnet-20240620", max_tokens: int = 800, temperature: float = 0.7):
    """Call Claude API and return raw response."""
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set in environment."}

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(ANTHROPIC_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract text from content blocks
            content = data.get("content", [])
            if isinstance(content, list):
                text = ""
                for block in content:
                    if block.get("type") == "text":
                        text += block.get("text", "")
                return {"text": text, "raw": data}
            
            return {"text": str(data), "raw": data}
    except Exception as e:
        logger.exception("Error calling Claude API: %s", e)
        return {"error": str(e)}

async def call_claude_json(prompt: str, model: str = "claude-3-5-sonnet-20240620", max_tokens: int = 1200, temperature: float = 0.1):
    """Call Claude and parse JSON response."""
    raw_response = await call_claude_raw(prompt, model, max_tokens, temperature)
    
    if "error" in raw_response:
        return {"error": raw_response["error"], "raw": raw_response.get("raw")}
    
    text = raw_response.get("text", "")
    try:
        parsed = _extract_json_from_text(text)
        return parsed
    except Exception as e:
        logger.warning("Failed to parse JSON from Claude output: %s", e)
        return {"error": "Failed to parse JSON response", "raw_text": text}
