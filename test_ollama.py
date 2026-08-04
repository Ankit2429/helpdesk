#!/usr/bin/env python
"""
test_ollama.py

Automated test script for verifying Ollama integration in AUNTII Helpdesk Robot.
Tests:
1. Connection to Ollama server host.
2. Availability of target LLM model ('llama3.2:3b').
3. Successful generation of text response using LLMService.
"""

import sys
import logging
from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_MAX_TOKENS, OLLAMA_TIMEOUT
from services.llm_service import LLMService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_ollama")


def main() -> None:
    print("=" * 70)
    print("        AUNTII Offline AI Helpdesk Robot — Ollama Verification Test")
    print("=" * 70)

    print(f"\n[1] Initializing LLMService...")
    print(f"    - Host URL:      {OLLAMA_HOST}")
    print(f"    - Target Model:  {OLLAMA_MODEL}")
    print(f"    - Temperature:   {OLLAMA_TEMPERATURE}")
    print(f"    - Max Tokens:    {OLLAMA_MAX_TOKENS}")
    print(f"    - Timeout (s):   {OLLAMA_TIMEOUT}")

    llm = LLMService(
        model=OLLAMA_MODEL,
        host=OLLAMA_HOST,
        temperature=OLLAMA_TEMPERATURE,
        max_tokens=OLLAMA_MAX_TOKENS,
        timeout=OLLAMA_TIMEOUT,
    )

    print("\n[2] Testing Ollama connection and checking model availability...")
    is_ok, msg = llm.check_connection()
    print(f"    Status:  {'PASSED [OK]' if is_ok else 'FAILED [ERROR]'}")
    print(f"    Message:\n{msg}")

    if not is_ok:
        print("\n" + "!" * 70)
        print("VERIFICATION FAILED: Ollama server or model is unavailable.")
        if "ollama pull" in msg:
            print("\nAction Required:")
            print(f"    Please open terminal and pull the required model:")
            print(f'    & "$env:LOCALAPPDATA\\Programs\\Ollama\\ollama.exe" pull {OLLAMA_MODEL}')
            print(f"    (or 'ollama pull {OLLAMA_MODEL}' if added to system PATH)")
        else:
            print("\nAction Required:")
            print("    Please start your local Ollama desktop service / server.")
        print("!" * 70 + "\n")
        sys.exit(1)

    print("\n[3] Testing text response generation...")
    test_prompt = (
        "System:\n"
        "You are AUNTII, an offline AI campus helpdesk assistant.\n\n"
        "Context:\n"
        "KLE Technological University (BVB) is located in Vidyanagar, Hubballi, Karnataka.\n\n"
        "User Question:\n"
        "Where is KLE Tech located?\n\n"
        "Answer only using the provided context whenever possible. If insufficient information exists, clearly state that."
    )

    print(f"    Input Prompt:\n{test_prompt}\n")
    print("    Generating response via Ollama...")
    response = llm.generate(test_prompt)

    print("\n[4] Ollama Response Output:")
    print("-" * 70)
    print(response)
    print("-" * 70)

    if response and not response.startswith("[AUNTII Offline Service Warning]"):
        print("\nSUCCESS: Ollama connection, model availability, and text generation verified!")
    else:
        print("\nWARNING: Response generation returned a warning or failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
