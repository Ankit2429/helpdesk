"""Production-grade Offline Interactive RAG Chat Application.

Integrates ChromaRetriever with local Ollama LLM service (default: llama3.1:8b),
enforces strict anti-hallucination prompting, logs conversation history, and provides
a rich interactive CLI display with timing, confidence, and source citations.
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import numpy as np
from langchain_core.documents import Document

from config.config import LOGS_DIR
from logger.logger import get_logger
from retrieval.retriever import ChromaRetriever

logger = get_logger("chat_application")

DEFAULT_MODEL: str = "llama3.1:8b"
OLLAMA_API_URL: str = "http://localhost:11434/api/generate"
CHAT_HISTORY_FILE: Path = LOGS_DIR / "chat_history.json"

PROMPT_TEMPLATE: str = """You are an AI Campus Helpdesk Assistant for KLE Technological University (formerly BVBCET), Hubballi.

Instructions:
1. Answer the user's question ONLY using the retrieved context provided below.
2. If the answer cannot be found in the provided context, reply EXACTLY:
   "I couldn't find that information in the college knowledge base."
3. Never make up, infer, or hallucinate any facts, dates, names, or fee structures not explicitly stated.

Context Information:
--------------------------------------------------
{context}
--------------------------------------------------

User Question: {question}

Answer:"""


class ChatHistoryLogger:
    """Manages persistent conversation history logging."""

    def __init__(self, log_file: Path = CHAT_HISTORY_FILE) -> None:
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load conversation log if present."""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def log_turn(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> None:
        """Append a single Q&A turn to the history log."""
        turn = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": question,
            "answer": answer,
            "sources": sources,
            "metrics": metrics,
        }
        self.history.append(turn)
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed persisting conversation log: {e}")


class RAGChatEngine:
    """RAG Chat Engine orchestrating retrieval, Ollama LLM generation, and metrics collection."""

    def __init__(
        self,
        llm_model: str = DEFAULT_MODEL,
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        top_k: int = 5,
        score_threshold: float = 0.0,
        ollama_url: str = OLLAMA_API_URL,
        persist_dir: Path = Path("vector_db/chroma"),
    ) -> None:
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.ollama_url = ollama_url

        self.retriever = ChromaRetriever(
            model_name=embedding_model,
            persist_dir=persist_dir,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        self.history_logger = ChatHistoryLogger()

    def generate_llm_answer(self, prompt: str) -> Tuple[str, float]:
        """Call Ollama LLM endpoint. Returns (answer_text, inference_time_seconds)."""
        start_time = time.time()
        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        }

        try:
            resp = requests.post(self.ollama_url, json=payload, timeout=60)
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip()
                if not answer:
                    answer = "I couldn't find that information in the college knowledge base."
                return answer, elapsed
            else:
                logger.error(f"Ollama HTTP error {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Error connecting to Ollama LLM at {self.ollama_url}: {err}")

        elapsed = round(time.time() - start_time, 2)
        return "I couldn't find that information in the college knowledge base.", elapsed

    def ask(
        self,
        question: str,
        category: Optional[str] = None,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process question through Retriever and Ollama LLM pipeline."""
        search_start = time.time()

        # Step 1: Retrieve Top 5 chunks
        retrieved_docs: List[Document] = self.retriever.retrieve(
            question=question,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            category=category,
            department=department,
            rerank=True,
        )
        search_time_ms = round((time.time() - search_start) * 1000, 2)

        # Handle case when no context is retrieved
        if not retrieved_docs:
            answer = "I couldn't find that information in the college knowledge base."
            metrics = {
                "confidence": 0.0,
                "search_time_ms": search_time_ms,
                "inference_time_s": 0.0,
            }
            self.history_logger.log_turn(question, answer, [], metrics)
            return {
                "question": question,
                "answer": answer,
                "sources": [],
                "metrics": metrics,
            }

        # Step 2: Format context and prompt
        context_blocks = []
        sources_summary = []
        scores = []

        for idx, doc in enumerate(retrieved_docs, start=1):
            meta = doc.metadata
            score = meta.get("score", 0.0)
            scores.append(score)

            context_blocks.append(f"[Document #{idx}]\n{doc.page_content.strip()}")
            sources_summary.append(
                {
                    "chunk_id": meta.get("chunk_id", ""),
                    "heading": meta.get("heading", ""),
                    "source": meta.get("source", ""),
                    "relative_path": meta.get("relative_path", ""),
                    "category": meta.get("category", ""),
                    "score": score,
                }
            )

        context_str = "\n\n".join(context_blocks)
        prompt = PROMPT_TEMPLATE.format(context=context_str, question=question)

        # Step 3: LLM Inference
        answer, inference_time_s = self.generate_llm_answer(prompt)
        confidence = round(float(np.mean(scores)), 4) if scores else 0.0

        metrics = {
            "confidence": confidence,
            "search_time_ms": search_time_ms,
            "inference_time_s": inference_time_s,
        }

        # Step 4: Log conversation turn
        self.history_logger.log_turn(question, answer, sources_summary, metrics)

        return {
            "question": question,
            "answer": answer,
            "sources": sources_summary,
            "metrics": metrics,
        }


def display_turn_result(result: Dict[str, Any]) -> None:
    """Print formatted result to terminal CLI."""
    ans = result["answer"]
    metrics = result["metrics"]
    sources = result["sources"]

    print("\n" + "=" * 65)
    print("ANSWER")
    print("=" * 65)
    print(ans)
    print("\n" + "-" * 65)
    print("METRICS & CONFIDENCE")
    print("-" * 65)
    print(f"Confidence Score : {metrics['confidence']:.4f}")
    print(f"Search Time      : {metrics['search_time_ms']} ms")
    print(f"Inference Time   : {metrics['inference_time_s']} s")

    if sources:
        print("\n" + "-" * 65)
        print("RETRIEVED SOURCES (Top 5)")
        print("-" * 65)
        for idx, src in enumerate(sources, start=1):
            print(f"[{idx}] Heading: {src['heading'] or 'Overview'}")
            print(f"    Category     : {src['category']}")
            print(f"    Source File  : {src['source']}")
            print(f"    Relative Path: {src['relative_path']}")
            print(f"    Match Score  : {src['score']:.4f}")
    print("=" * 65 + "\n")


def interactive_cli(engine: RAGChatEngine) -> None:
    """Run interactive question prompt loop."""
    print("=" * 65)
    print("  BVBCET / KLE TECH OFFLINE AI RAG CHATBOT")
    print(f"  LLM Model: {engine.llm_model} | Retriever: ChromaDB")
    print("  Type 'exit' or 'quit' to end session.")
    print("=" * 65 + "\n")

    while True:
        try:
            user_input = input("Question > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Ending chat session. Goodbye!")
                break

            result = engine.ask(user_input)
            display_turn_result(result)

        except (KeyboardInterrupt, EOFError):
            print("\nChat session terminated.")
            break


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for chat application."""
    parser = argparse.ArgumentParser(description="Offline RAG Chatbot Application")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Ollama LLM model name (default: llama3.1:8b)")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="Top K chunks to retrieve")
    parser.add_argument("-t", "--threshold", type=float, default=0.0, help="Similarity score threshold")
    parser.add_argument("--url", type=str, default=OLLAMA_API_URL, help="Ollama API endpoint URL")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python chat.py."""
    args = parse_args()
    engine = RAGChatEngine(
        llm_model=args.model,
        top_k=args.top_k,
        score_threshold=args.threshold,
        ollama_url=args.url,
    )
    interactive_cli(engine)


if __name__ == "__main__":
    main()
