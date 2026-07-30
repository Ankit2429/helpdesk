"""Production-grade Offline Interactive RAG Chat Application CLI.

Delegates conversation flow to ConversationManager (Intent Detection -> Memory ->
Query Rewriter -> Retriever -> Reranker -> Prompt Builder -> Local LLM -> Response Generator).
Supports interactive slash commands (/reset, /history, /context, /help).
"""

import argparse
from pathlib import Path
import sys
from typing import Any, Dict

# Ensure bvbcet_rag_pipeline package root is on sys.path
pipeline_dir = Path(__file__).resolve().parent
if str(pipeline_dir) not in sys.path:
    sys.path.insert(0, str(pipeline_dir))

from conversation.conversation_manager import ConversationManager
from llm.prompt_builder import V2_GROUNDED_CONCISE_SYSTEM_PROMPT

PROMPT_TEMPLATE: str = V2_GROUNDED_CONCISE_SYSTEM_PROMPT
from logger.logger import get_logger

logger = get_logger("chat_cli")


class ChatHistoryLogger:
    """Compatibility logger wrapper for chat history."""

    def __init__(self, log_file: Any = None) -> None:
        self.log_file = log_file

    def log_turn(self, question: str, answer: str, sources: Any, metrics: Any) -> None:
        if self.log_file:
            import json, datetime
            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "question": question,
                "answer": answer,
                "sources": sources,
                "metrics": metrics,
            }
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            existing.append(entry)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)

    def clear(self) -> None:
        if self.log_file and Path(self.log_file).exists():
            Path(self.log_file).unlink()


class RAGChatEngine:
    """Facade wrapping ConversationManager for backward compatibility."""

    def __init__(
        self,
        llm_model: str = "llama3.1:8b",
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        score_threshold: float = 0.35,
        session_id: str = "default_session",
        prompt_version: str = "v2_grounded_concise",
        **kwargs,
    ) -> None:
        self.llm_model = llm_model
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.prompt_version = prompt_version
        self.history_logger = ChatHistoryLogger()

        self.manager = ConversationManager(
            top_k=top_k,
            score_threshold=score_threshold,
        )
        self.summarizer = self.manager.memory

    @property
    def retriever(self) -> Any:
        """Backward compatibility property for retriever."""
        return self.manager.retriever

    @retriever.setter
    def retriever(self, val: Any) -> None:
        self.manager.retriever = val

    def ask(self, question: str, category: Any = None, department: Any = None) -> Dict[str, Any]:
        """Delegate turn execution to ConversationManager."""
        # Use generate_llm_answer if patched
        if hasattr(self, "generate_llm_answer") and callable(self.generate_llm_answer):
            self.manager.llm_inference.generate = self.generate_llm_answer
        res = self.manager.handle(question)
        if self.history_logger and hasattr(self.history_logger, "log_turn"):
            self.history_logger.log_turn(
                question=question,
                answer=res.answer,
                sources=res.citations,
                metrics=res.metrics,
            )
        return res.to_dict()

    def generate_llm_answer(self, prompt: str) -> Any:
        """Backward compatibility method for legacy unit tests."""
        raw_ans, elapsed, err = self.manager.llm_inference.generate(prompt)
        return raw_ans, elapsed, err

    def reset_conversation(self) -> None:
        """Reset conversation session."""
        self.manager.reset_session()


def print_banner() -> None:
    """Print welcome header for CLI chat interface."""
    print("=" * 70)
    print("  KLE TECHNOLOGICAL UNIVERSITY AI CAMPUS HELPDESK ROBOT (OFFLINE RAG)")
    print("=" * 70)
    print("  Type your question below (or type '/help' for slash commands, 'exit' to quit)")
    print("-" * 70)


def print_help() -> None:
    """Print available interactive CLI slash commands."""
    print("\n--- AVAILABLE COMMANDS ---")
    print("  /reset   : Clear active conversation memory and reset state")
    print("  /history : View recent turn history")
    print("  /context : View active session state")
    print("  /help    : Display this help message")
    print("  exit     : Terminate interactive chat session\n")


def run_cli() -> None:
    """Main CLI loop executing user queries via ConversationManager."""
    parser = argparse.ArgumentParser(description="KLE Tech AI Helpdesk Interactive CLI")
    parser.add_argument("--model", type=str, default="llama3.1:8b", help="Ollama LLM model name")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K retrieval limit")
    args = parser.parse_args()

    print_banner()
    manager = ConversationManager(top_k=args.top_k)

    while True:
        try:
            user_input = input("\nUser > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated. Goodbye!")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Session terminated. Goodbye!")
            break

        # Handle Slash Commands
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/reset":
                manager.reset_session()
                print("✓ Active conversation memory reset successfully.")
            elif cmd == "/history":
                history = manager.memory.get_history()
                print(f"\n--- Conversation History ({len(history)} messages) ---")
                for msg in history:
                    print(f"[{msg.role.upper()}]: {msg.content}")
            elif cmd == "/context":
                print(f"\nActive Session Memory: {len(manager.memory.get_history())} messages logged.")
            elif cmd == "/help":
                print_help()
            else:
                print(f"Unknown command '{user_input}'. Type '/help' for assistance.")
            continue

        # Execute Query through ConversationManager
        response = manager.handle(user_input)

        # Print Formatted Response
        print(f"\nAssistant [{response.intent.value}] > {response.answer}")
        if response.citations:
            print("\n📚 Sources:")
            for cit in response.citations:
                print(f"  - [{cit['citation_number']}] {cit['source']} (Heading: '{cit['heading']}', Score: {cit['score']:.4f})")


if __name__ == "__main__":
    run_cli()
