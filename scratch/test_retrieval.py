import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.abspath('src'))

from campus_helpdesk.touch_app import build_chat_service

print("Building chat service...")
chat_service = build_chat_service()

queries = [
    "Who is the principal of BVBCET?",
    "Who is the principal of KLE Technological University?",
    "Tell me about hostel facilities",
    "What are the engineering courses offered?",
    "How to get admission in KLE Tech?"
]

for q in queries:
    print("\n" + "="*50)
    print(f"QUERY: {q}")
    res = chat_service.respond(q)
    print(f"REPLY: {res.reply}")
    print(f"CONFIDENCE SCORE: {res.confidence_score}")
    print(f"CONFIDENCE LEVEL: {res.confidence_level}")
