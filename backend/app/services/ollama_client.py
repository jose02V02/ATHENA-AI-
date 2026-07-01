import httpx
import json
from app.core.config import settings

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
    
    async def generate_stream(self, prompt: str, context: list = None):
        """Streaming generation per UX ChatGPT-like"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True
        }
        if context:
            payload["context"] = context
            
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", 
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield data.get("response", "")
                        if data.get("done"):
                            break
    
    async def list_models(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/api/tags")
            return r.json().get("models", [])

ollama = OllamaClient()
