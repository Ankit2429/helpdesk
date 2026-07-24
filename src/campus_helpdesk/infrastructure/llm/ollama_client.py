import requests

class OllamaClient:
    def __init__(self, model="llama3.2:3b"):
        self.url = "http://localhost:11434/api/generate"
        self.model = model

    def generate(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(self.url, json=payload)
        return response.json()["response"]