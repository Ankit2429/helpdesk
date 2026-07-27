"""
token_benchmark.py
Measures exact generated token counts (eval_count), prompt tokens (prompt_eval_count),
eval duration, tokens/second, and latency across English, Hindi, and Kannada for LLM evaluation.
"""

import json
import logging
import os
import sys
import time
import urllib.request

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OLLAMA_NUM_GPU"] = "0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

OLLAMA_URL = "http://localhost:11434/api/chat"

PROMPTS = [
    ("en", "Where is the library located in campus?", "The Central Library is located at Block C, 2nd floor."),
    ("hi", "पुस्तकालय की जानकारी दें", "बीवीबी इंजीनियरिंग कॉलेज का पुस्तकालय ब्लॉक सी, दूसरी मंजिल पर स्थित है।"),
    ("kn", "ಕ್ಯಾಂಪಸ್ ಸಹಾಯ ಕೇಂದ್ರ ಎಲ್ಲಿದೆ?", "ಕ್ಯಾಂಪಸ್ ಸಹಾಯ ಕೇಂದ್ರವು ಬ್ಲಾಕ್ ಸಿ, ಎರಡನೇ ಮಹಡಿಯಲ್ಲಿದೆ."),
]


def query_ollama(model_name: str, prompt_text: str, max_tokens: int = 128) -> dict:
    """Send chat request directly to Ollama API and return complete metrics dict."""
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a campus helpdesk assistant. Be extremely concise. Answer in 1 short sentence only.",
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ],
        "options": {
            "num_gpu": 0,
            "temperature": 0.0,
            "num_predict": max_tokens,
            "num_thread": 6,
        },
        "stream": False,
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0

    res_data["total_client_latency_sec"] = elapsed
    return res_data


def benchmark_model(model_name: str, max_tokens: int = 128):
    print("\n" + "=" * 70)
    print(f"      OLLAMA TOKEN COUNTS & LATENCY BENCHMARK: [{model_name}]")
    print(f"      (Forced CPU-Only Execution, max_tokens={max_tokens})")
    print("=" * 70)

    metrics = []

    for lang, prompt, expected in PROMPTS:
        print(f"\n>>> Querying [{model_name}] ({lang.upper()}): \"{prompt}\"")
        try:
            data = query_ollama(model_name, prompt, max_tokens=max_tokens)
            
            message_content = data.get("message", {}).get("content", "").strip()
            prompt_tokens = data.get("prompt_eval_count", 0)
            gen_tokens = data.get("eval_count", 0)
            eval_dur_ns = data.get("eval_duration", 1)
            eval_dur_sec = eval_dur_ns / 1e9 if eval_dur_ns else 0.001
            tokens_per_sec = gen_tokens / eval_dur_sec if eval_dur_sec > 0 else 0
            client_latency = data.get("total_client_latency_sec", 0.0)

            m = {
                "model": model_name,
                "lang": lang,
                "prompt": prompt,
                "response": message_content,
                "prompt_tokens": prompt_tokens,
                "gen_tokens": gen_tokens,
                "eval_dur_sec": eval_dur_sec,
                "tokens_per_sec": tokens_per_sec,
                "client_latency": client_latency,
            }
            metrics.append(m)

            print(f"    Answer          : \"{message_content}\"")
            print(f"    Prompt Tokens   : {prompt_tokens}")
            print(f"    Generated Tokens: {gen_tokens}")
            print(f"    Gen Duration    : {eval_dur_sec:.2f} s")
            print(f"    Gen Speed       : {tokens_per_sec:.2f} tokens/sec")
            print(f"    Total Latency   : {client_latency:.2f} s")

        except Exception as e:
            print(f"    ERROR querying model: {e}")

    print("\n" + "=" * 75)
    print(f" SUMMARY METRICS TABLE FOR [{model_name}]:")
    print("=" * 75)
    print(f"{'Lang':<6} | {'Generated Tokens':<18} | {'Tokens/Sec':<12} | {'Eval Duration':<14} | {'Total Latency'}")
    print("-" * 75)
    for m in metrics:
        print(f"{m['lang'].upper():<6} | {m['gen_tokens']:<18} | {m['tokens_per_sec']:<12.2f} | {m['eval_dur_sec']:<14.2f} | {m['client_latency']:.2f}s")
    print("=" * 75)
    return metrics


if __name__ == "__main__":
    benchmark_model("llama3.2:3b", max_tokens=128)
