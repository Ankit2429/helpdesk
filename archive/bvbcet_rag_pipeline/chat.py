"""Production-grade Offline Interactive RAG Chat Application.

Integrates ChromaRetriever with Conversation Manager (Topic Tracker, Entity Resolver,
and Conversation Summarizer) and local Ollama LLM service (default: llama3.1:8b).
Enforces strict anti-hallucination prompting, logs conversation history, and provides
a rich interactive CLI display with slash commands (/reset, /history, /context, /help).
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from langchain_core.documents import Document

from config.config import LOGS_DIR
from conversation_manager.entity_resolver import EntityResult, EntityResolver
from conversation_manager.summarizer import ConversationSummarizer, SummaryResult
from conversation_manager.topic_tracker import TopicResult, TopicTracker
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

{conversation_summary_block}

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

    def clear(self) -> None:
        """Clear history log."""
        self.history = []
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        except Exception as e:
            logger.error(f"Failed clearing conversation log: {e}")


def check_ollama_status(model_name: str, ollama_url: str = OLLAMA_API_URL) -> Tuple[bool, str]:
    """Pre-flight check connecting to Ollama tags endpoint and verifying requested model is installed."""
    tags_url = ollama_url.replace("/api/generate", "/api/tags")
    try:
        resp = requests.get(tags_url, timeout=5)
        if resp.status_code != 200:
            return False, f"Could not reach Ollama API at '{tags_url}' (HTTP status {resp.status_code})."

        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]

        has_model = any(model_name == m or m.startswith(f"{model_name}:") or model_name.startswith(m.split(":")[0]) for m in models)
        if not has_model:
            return (
                False,
                f"Model '{model_name}' not found in local Ollama service. "
                f"Available models: {models}. "
                f"Please run `ollama pull {model_name}` or pass --model with an available model name."
            )
        return True, f"Ollama pre-flight check passed. Model '{model_name}' is ready."
    except Exception as err:
        return False, f"Ollama pre-flight check failed: Could not connect to '{tags_url}' ({err}). Please ensure Ollama service is running."


class RAGChatEngine:
    """Integrated RAG Chat Engine with Topic Tracker, Entity Resolver, and Conversation Memory."""

    def __init__(
        self,
        llm_model: str = DEFAULT_MODEL,
        embedding_model: str = "all-MiniLM-L6-v2",
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

        # Conversation Manager Subsystems
        self.topic_tracker = TopicTracker(model_name=embedding_model)
        self.entity_resolver = EntityResolver()
        self.summarizer = ConversationSummarizer(token_budget=1024, max_unsummarized_turns=6)

    def reset_conversation(self) -> None:
        """Reset conversation history, memory, topic tracker, and entity resolver state."""
        self.topic_tracker = TopicTracker(model_name=self.embedding_model)
        self.entity_resolver = EntityResolver()
        self.summarizer = ConversationSummarizer(token_budget=1024, max_unsummarized_turns=6)
        self.history_logger.clear()
        logger.info("Conversation state and memory reset.")

    def generate_llm_answer(self, prompt: str) -> Tuple[Optional[str], float, Optional[str]]:
        """Call Ollama LLM endpoint. Returns (answer_text, inference_time_seconds, error_detail)."""
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
                    return None, elapsed, "Ollama returned an empty response."
                return answer, elapsed, None
            else:
                error_msg = f"Ollama HTTP error {resp.status_code}: {resp.text.strip()}"
                logger.error(error_msg)
                return None, elapsed, error_msg
        except Exception as err:
            error_msg = f"Error connecting to Ollama LLM at {self.ollama_url}: {err}"
            logger.error(error_msg)
            elapsed = round(time.time() - start_time, 2)
            return None, elapsed, error_msg

    def ask(
        self,
        question: str,
        category: Optional[str] = None,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process turn: Topic Tracking -> Entity Resolution -> Retrieval -> Prompt -> LLM -> Memory Update."""
        search_start = time.time()

        # Step 1: Memory & Context
        summary_state: SummaryResult = self.summarizer.get_summary()

        # Step 2: Topic Tracker
        topic_res: TopicResult = self.topic_tracker.process_turn(question)
        current_topic = topic_res.active_topic

        # Step 3: Entity Resolver
        entity_res: EntityResult = self.entity_resolver.resolve(
            question,
            conversation_context=summary_state.current_context,
        )
        resolved_query = entity_res.resolved_query
        resolved_entities = entity_res.extracted_entities

        # Step 4: Retriever using resolved query
        retrieved_docs: List[Document] = self.retriever.retrieve(
            question=resolved_query,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            category=category or (current_topic.lower() if current_topic in ["Departments", "Hostels", "Admissions"] else None),
            department=department,
            rerank=True,
        )
        search_time_ms = round((time.time() - search_start) * 1000, 2)

        # Handle case when no context is retrieved
        if not retrieved_docs:
            answer = "I couldn't find that information in the college knowledge base."
            metrics = {
                "confidence": 0.0,
                "topic_confidence": topic_res.topic_confidence,
                "entity_confidence": entity_res.entity_confidence,
                "search_time_ms": search_time_ms,
                "inference_time_s": 0.0,
            }
            # Update memory
            self.summarizer.add_turn(question, answer, entities=resolved_entities, topic=current_topic)
            return {
                "question": question,
                "resolved_query": resolved_query,
                "answer": answer,
                "current_topic": current_topic,
                "resolved_entities": resolved_entities,
                "resolved_references": entity_res.resolved_references,
                "sources": [],
                "metrics": metrics,
                "status": "zero_retrieval",
                "error_detail": None,
            }

        # Step 5: Format context and prompt
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
        summary_block = (
            f"Prior Conversation Summary:\n{summary_state.conversation_summary}\n"
            if summary_state.summarized_turns > 0
            else ""
        )

        prompt = PROMPT_TEMPLATE.format(
            conversation_summary_block=summary_block,
            context=context_str,
            question=resolved_query,
        )

        # Step 6: LLM Inference
        llm_answer, inference_time_s, error_detail = self.generate_llm_answer(prompt)
        confidence = round(float(np.mean(scores)), 4) if scores else 0.0

        if error_detail or llm_answer is None:
            status = "llm_error"
            answer = (
                f"Retrieved relevant context ({len(retrieved_docs)} chunks), but the language model failed to generate a response.\n"
                f"Ollama Error Details: {error_detail}\n"
                f"Please verify the model is pulled (`ollama list`) and Ollama is running."
            )
        else:
            status = "success"
            answer = llm_answer

        metrics = {
            "confidence": confidence,
            "topic_confidence": topic_res.topic_confidence,
            "entity_confidence": entity_res.entity_confidence,
            "search_time_ms": search_time_ms,
            "inference_time_s": inference_time_s,
        }

        # Step 7: Memory Update
        self.summarizer.add_turn(
            question=question,
            answer=answer,
            entities=resolved_entities,
            topic=current_topic,
        )
        self.history_logger.log_turn(question, answer, sources_summary, metrics)

        return {
            "question": question,
            "resolved_query": resolved_query,
            "answer": answer,
            "current_topic": current_topic,
            "resolved_entities": resolved_entities,
            "resolved_references": entity_res.resolved_references,
            "sources": sources_summary,
            "metrics": metrics,
            "status": status,
            "error_detail": error_detail,
        }


def display_turn_result(result: Dict[str, Any]) -> None:
    """Print mandatory result fields: Answer, Retrieved Sources, Confidence, Current Topic, Resolved Entities."""
    ans = result["answer"]
    metrics = result["metrics"]
    sources = result["sources"]
    current_topic = result.get("current_topic", "General")
    resolved_entities = result.get("resolved_entities", {})
    resolved_refs = result.get("resolved_references", {})
    resolved_query = result.get("resolved_query", result["question"])
    status = result.get("status", "success")

    print("\n" + "=" * 65)
    if status == "llm_error":
        print("ANSWER (GENERATION FAILURE)")
    else:
        print("ANSWER")
    print("=" * 65)
    print(ans)

    print("\n" + "-" * 65)
    print("CURRENT TOPIC & RESOLVED ENTITIES")
    print("-" * 65)
    print(f"Current Topic     : {current_topic}")
    print(f"Original Question : {result['question']}")
    print(f"Resolved Query    : {resolved_query}")
    print(f"Resolved Entities : {resolved_entities if resolved_entities else 'None'}")
    if resolved_refs:
        print(f"Pronoun Mapping   : {resolved_refs}")

    print("\n" + "-" * 65)
    print("METRICS & CONFIDENCE")
    print("-" * 65)
    print(f"Vector Match Confidence : {metrics.get('confidence', 0.0):.4f}")
    print(f"Topic Confidence        : {metrics.get('topic_confidence', 0.0):.4f}")
    print(f"Entity Confidence       : {metrics.get('entity_confidence', 0.0):.4f}")
    print(f"Search Time             : {metrics.get('search_time_ms', 0.0)} ms")
    print(f"Inference Time          : {metrics.get('inference_time_s', 0.0)} s")

    if status == "llm_error":
        print("\n" + "-" * 65)
        print("CONTEXT RETRIEVED BUT NOT USED DUE TO GENERATION FAILURE")
        print("-" * 65)
        print(f"Retrieved Chunks : {len(sources)} chunks found")
        if sources:
            for idx, src in enumerate(sources, start=1):
                print(f"  [{idx}] {src['source']} (Heading: '{src['heading'] or 'Overview'}', Score: {src['score']:.4f})")
        print("=" * 65 + "\n")
        return

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


def display_help() -> None:
    """Print CLI Slash Commands guide."""
    print("\n" + "=" * 65)
    print("AVAILABLE SLASH COMMANDS")
    print("=" * 65)
    print("  /reset   : Clear conversation memory, reset entities and topic state.")
    print("  /history : View past Q&A turns stored in memory log.")
    print("  /context : View current memory summary, active entities, and active topic.")
    print("  /help    : Display this help message.")
    print("  exit     : Terminate chatbot session.")
    print("=" * 65 + "\n")


def display_context(engine: RAGChatEngine) -> None:
    """Display active memory summary, entities, and active topic."""
    summary_state = engine.summarizer.get_summary()
    print("\n" + "=" * 65)
    print("ACTIVE CONVERSATION MEMORY & CONTEXT")
    print("=" * 65)
    print(f"Active Topic       : {engine.topic_tracker.current_topic or 'None'}")
    print(f"Active Entities    : {summary_state.active_entities if summary_state.active_entities else 'None'}")
    print(f"Topics Discussed   : {summary_state.topics_discussed}")
    print(f"Total Turns        : {summary_state.total_turns}")
    print(f"Summarized Turns   : {summary_state.summarized_turns}")
    print(f"Estimated Tokens   : {summary_state.estimated_tokens} / {engine.summarizer.token_budget}")
    print("-" * 65)
    print("Conversation Summary:")
    print(summary_state.conversation_summary)
    print("=" * 65 + "\n")


def display_history(engine: RAGChatEngine) -> None:
    """Display history log."""
    history = engine.history_logger.history
    print("\n" + "=" * 65)
    print(f"CONVERSATION HISTORY ({len(history)} turns)")
    print("=" * 65)
    if not history:
        print("No conversation history recorded yet.")
    else:
        for idx, turn in enumerate(history, start=1):
            print(f"Turn #{idx} [{turn.get('timestamp', '')}]")
            print(f"  Q: {turn.get('question', '')}")
            print(f"  A: {turn.get('answer', '')[:120]}...")
            print("-" * 65)
    print("=" * 65 + "\n")


def interactive_cli(engine: RAGChatEngine) -> None:
    """Run interactive CLI prompt loop supporting slash commands."""
    print("=" * 65)
    print("  BVBCET / KLE TECH OFFLINE AI RAG CHATBOT")
    print(f"  LLM Model: {engine.llm_model} | Retriever: ChromaDB")
    print("  Commands: /reset | /history | /context | /help | exit")
    print("=" * 65 + "\n")

    while True:
        try:
            user_input = input("Question > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Ending chat session. Goodbye!")
                break

            # Handle Slash Commands
            cmd = user_input.lower()
            if cmd == "/reset":
                engine.reset_conversation()
                print("Conversation state, memory, and entity history reset successfully.")
                continue
            elif cmd == "/history":
                display_history(engine)
                continue
            elif cmd == "/context":
                display_context(engine)
                continue
            elif cmd == "/help":
                display_help()
                continue

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

    # Pre-flight check
    is_ok, status_msg = check_ollama_status(model_name=args.model, ollama_url=args.url)
    if not is_ok:
        print("\n" + "!" * 65)
        print("OLLAMA PRE-FLIGHT CHECK WARNING / ERROR")
        print("!" * 65)
        print(status_msg)
        print("!" * 65 + "\n")

    engine = RAGChatEngine(
        llm_model=args.model,
        top_k=args.top_k,
        score_threshold=args.threshold,
        ollama_url=args.url,
    )
    interactive_cli(engine)


if __name__ == "__main__":
    main()
