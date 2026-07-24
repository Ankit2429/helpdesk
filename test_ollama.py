import requests

url = "http://localhost:11434/api/generate"

payload = {
    "model": "llama3.2:3b",
    "prompt": "Who are you?",
    "stream": False
}

response = requests.post(url, json=payload)
print(response.json()["response"])
