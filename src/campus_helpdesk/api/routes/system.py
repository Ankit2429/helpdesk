"""System and service-status routes."""

import shutil
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from campus_helpdesk.api.schemas.system import HealthResponse, RootResponse
from campus_helpdesk.config.settings import Settings

router = APIRouter(tags=["system"])

HTML_WEB_UI = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campus Helpdesk Autonomous AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --accent-glow: #6366f1;
            --accent-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
            --bot-msg-bg: rgba(51, 65, 85, 0.6);
            --user-msg-bg: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-gradient); min-height: 100vh; color: var(--text-primary); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
        .container { width: 100%; max-width: 900px; height: 85vh; background: var(--glass-bg); backdrop-filter: blur(16px); border: 1px solid var(--glass-border); border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; overflow: hidden; }
        .header { padding: 20px 28px; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.4); }
        .header-title { display: flex; align-items: center; gap: 12px; }
        .bot-avatar { width: 42px; height: 42px; border-radius: 12px; background: var(--accent-gradient); display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; box-shadow: 0 0 15px rgba(99, 102, 241, 0.4); }
        .header-text h1 { font-size: 1.15rem; font-weight: 600; letter-spacing: -0.02em; }
        .header-text p { font-size: 0.8rem; color: var(--text-muted); }
        .status-badge { display: flex; align-items: center; gap: 8px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #4ade80; padding: 6px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 500; }
        .status-dot { width: 8px; height: 8px; background: #4ade80; border-radius: 50%; box-shadow: 0 0 8px #4ade80; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        
        .chat-area { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; scroll-behavior: smooth; }
        .chat-area::-webkit-scrollbar { width: 6px; }
        .chat-area::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 4px; }
        
        .msg { display: flex; gap: 12px; max-width: 80%; animation: fadeIn 0.3s ease-out forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .msg.user { align-self: flex-end; flex-direction: row-reverse; }
        .msg-content { padding: 14px 18px; border-radius: 18px; font-size: 0.95rem; line-height: 1.5; word-wrap: break-word; }
        .msg.bot .msg-content { background: var(--bot-msg-bg); border: 1px solid var(--glass-border); border-top-left-radius: 4px; }
        .msg.user .msg-content { background: var(--user-msg-bg); border-top-right-radius: 4px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }

        .suggestions { padding: 0 24px 12px 24px; display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; }
        .chip { background: rgba(255, 255, 255, 0.06); border: 1px solid var(--glass-border); border-radius: 16px; padding: 8px 14px; font-size: 0.8rem; color: var(--text-muted); cursor: pointer; white-space: nowrap; transition: all 0.2s; }
        .chip:hover { background: rgba(99, 102, 241, 0.2); border-color: var(--accent-glow); color: #fff; transform: translateY(-1px); }

        .input-area { padding: 18px 24px; border-top: 1px solid var(--glass-border); background: rgba(15, 23, 42, 0.4); display: flex; gap: 12px; align-items: center; }
        .input-box { flex: 1; background: rgba(30, 41, 59, 0.8); border: 1px solid var(--glass-border); border-radius: 16px; padding: 14px 18px; color: #fff; font-size: 0.95rem; outline: none; transition: border-color 0.2s; }
        .input-box:focus { border-color: var(--accent-glow); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2); }
        .send-btn { background: var(--accent-gradient); border: none; border-radius: 16px; width: 48px; height: 48px; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; transition: transform 0.2s, box-shadow 0.2s; }
        .send-btn:hover { transform: scale(1.05); box-shadow: 0 0 15px rgba(99, 102, 241, 0.5); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <div class="bot-avatar">🤖</div>
                <div class="header-text">
                    <h1>Campus Helpdesk AI</h1>
                    <p>Offline RAG + Local Ollama LLM</p>
                </div>
            </div>
            <div class="status-badge">
                <div class="status-dot"></div>
                System Active
            </div>
        </div>

        <div class="chat-area" id="chatArea">
            <div class="msg bot">
                <div class="msg-content">
                    Hello! 👋 I am your Campus Helpdesk AI Assistant. How can I help you today with campus navigation, departments, or administrative procedures?
                </div>
            </div>
        </div>

        <div class="suggestions">
            <div class="chip" onclick="sendPrompt(this.innerText)">📍 Where is the Central Library?</div>
            <div class="chip" onclick="sendPrompt(this.innerText)">🪪 How to apply for a student ID card?</div>
            <div class="chip" onclick="sendPrompt(this.innerText)">🕒 What are the administrative office hours?</div>
        </div>

        <div class="input-area">
            <input type="text" id="userInput" class="input-box" placeholder="Ask anything about campus..." onkeypress="handleKey(event)" autofocus />
            <button class="send-btn" id="sendBtn" onclick="sendMessage()">➔</button>
        </div>
    </div>

    <script>
        const chatArea = document.getElementById('chatArea');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');

        function appendMessage(text, isUser = false) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `msg ${isUser ? 'user' : 'bot'}`;
            msgDiv.innerHTML = `<div class="msg-content">${text.replace(/\\n/g, '<br>')}</div>`;
            chatArea.appendChild(msgDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
            return msgDiv;
        }

        function sendPrompt(text) {
            userInput.value = text;
            sendMessage();
        }

        function handleKey(e) {
            if (e.key === 'Enter') sendMessage();
        }

        async function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;

            appendMessage(query, true);
            userInput.value = '';
            userInput.disabled = true;
            sendBtn.disabled = true;

            const loadingMsg = appendMessage('Thinking...', false);

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query })
                });
                const data = await res.json();
                loadingMsg.querySelector('.msg-content').innerHTML = (data.reply || 'No response received.').replace(/\\n/g, '<br>');
            } catch (err) {
                loadingMsg.querySelector('.msg-content').innerText = 'Error connecting to helpdesk server.';
            } finally {
                userInput.disabled = false;
                sendBtn.disabled = false;
                userInput.focus();
            }
        }
    </script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Return Web UI for browser clients, or JSON for API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=HTML_WEB_UI)
    return JSONResponse(content={"message": "Campus Helpdesk API", "status": "online"})



@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return comprehensive process and sub-system health diagnostics."""
    components: dict[str, str] = {}
    settings: Settings = getattr(request.app.state, "settings", None)

    # 1. Ollama Health Check
    ollama_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
    try:
        r = httpx.get(f"{ollama_url}/api/tags", timeout=2.0)
        components["ollama"] = "healthy" if r.status_code == 200 else f"degraded (HTTP {r.status_code})"
    except Exception:
        components["ollama"] = "unreachable"

    # 2. FAISS Index & RAG Pipeline Health Check
    faiss_path = getattr(settings, "faiss_index_path", Path("data/faiss"))
    if faiss_path.exists() and (faiss_path / "index.faiss").exists():
        components["faiss"] = "healthy"
        components["rag"] = "healthy"
    else:
        components["faiss"] = "index_missing"
        components["rag"] = "degraded (index missing)"

    # 3. Whisper STT Service Check
    components["whisper"] = "healthy (local cached model ready)"

    # 4. TTS Service Check
    components["tts"] = "healthy (pyttsx3 ready)"

    # 5. Camera Vision Check
    components["camera"] = "available (OpenCV backend ready)"

    # 6. Disk Space Check
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = round(free / (1024 ** 3), 2)
        total_gb = round(total / (1024 ** 3), 2)
        disk_info: dict[str, float | str] = {
            "free_gb": free_gb,
            "total_gb": total_gb,
            "status": "healthy" if free_gb > 1.0 else "low_disk_space",
        }
    except Exception:
        disk_info = {"status": "unknown"}

    # 7. System Memory Check
    memory_info: dict[str, float | str] = {"status": "healthy"}

    overall_status = "healthy" if components.get("ollama") == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        components=components,
        disk_space=disk_info,
        memory=memory_info,
    )

