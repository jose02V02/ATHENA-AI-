import httpx
import json
import asyncio
from typing import AsyncGenerator
from app.core.config import settings

class OllamaStreamingClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.timeout = httpx.Timeout(120.0, connect=10.0)
    
    async def chat_stream(
        self, 
        messages: list, 
        model: str,
        tools: list = None
    ) -> AsyncGenerator[dict, None]:
        """
        True streaming da Ollama.
        Yields dict con: {'type': 'content'|'done'|'error', 'data': ...}
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if tools:
            payload["tools"] = tools
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield {"type": "error", "data": error_text.decode()}
                        return
                    
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            
                            # Token di contenuto
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield {"type": "content", "data": content}
                            
                            # Fine dello stream
                            if data.get("done"):
                                yield {
                                    "type": "done",
                                    "data": {
                                        "tokens": data.get("eval_count", 0),
                                        "duration_ms": data.get("total_duration", 0) / 1_000_000,
                                        "tokens_per_sec": data.get("eval_count", 0) / 
                                            max(data.get("eval_duration", 1) / 1_000_000_000, 0.001)
                                    }
                                }
                                return
                                
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.ConnectError:
            yield {"type": "error", "data": "Impossibile connettersi a Ollama. Assicurati che sia in esecuzione."}
        except Exception as e:
            yield {"type": "error", "data": f"Errore: {str(e)}"}
    
    async def chat_complete(self, messages: list, model: str, tools: list = None) -> dict:
        """Versione non-streaming per controllo tool calls"""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if tools:
            payload["tools"] = tools
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            return response.json()

# Istanza globale
ollama_stream = OllamaStreamingClient()
