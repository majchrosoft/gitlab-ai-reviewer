import os

import httpx


class LLM:
    def __init__(self):
        self.url = os.environ["OLLAMA_URL"].rstrip("/")
        self.model = os.environ["OLLAMA_MODEL"]

    def review(self, prompt):
        response = httpx.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "stream": False,
            },
            timeout=600,
        )

        response.raise_for_status()

        return response.json()["message"]["content"]
