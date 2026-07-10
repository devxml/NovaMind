import time
import uuid

from typing import Dict, Any, Optional


async def create_streaming_gemini_chunk(
        content: Optional[str] = None,
        role: Optional[str] = None,
        finish_reason: Optional[str] = None,
) -> Dict[str, Any]:
    chunk = {
        "id": f"gemini-{uuid.uuid4().hex}",
        "object": "gemini.content.chunk",
        "created": int(time.time()),
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason
            }
        ]
    }

    if content:
        chunk["choices"][0]["delta"]["content"] = content

    if role:
        chunk["choices"][0]["delta"]["role"] = role

    return chunk
