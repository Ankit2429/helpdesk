"""Modular Prompt Builder Engine.

Combines system persona instructions, conversation history, retrieved context documents,
and user question into a single formatted LLM prompt string.
"""

from typing import List, Optional
from langchain_core.documents import Document

from conversation.memory import ChatMessage
from logger.logger import get_logger

logger = get_logger("prompt_builder")

V2_GROUNDED_CONCISE_SYSTEM_PROMPT = """You are the official AI Campus Assistant for KLE Technological University (KLE Tech / BVBCET), located in Hubballi, Karnataka.
Your job is to answer student, parent, and visitor questions accurately and concisely using ONLY the provided context blocks.

STRICT GROUNDING & CONSTRAINTS:
1. Base your answer strictly on the provided Context Documents below. Do NOT hallucinate or assume facts not present in the context.
2. If the retrieved context does NOT contain sufficient facts to answer the question, state: "I couldn't find that information in the college knowledge base."
3. Keep your response concise (default 2 to 4 sentences). Do NOT add preamble or filler phrases like "Great question!", "Sure!", "As an AI assistant...".
4. Always maintain a polite, direct, and professional tone."""


class PromptBuilder:
    """Formats versioned system prompts with history, context, and question."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or V2_GROUNDED_CONCISE_SYSTEM_PROMPT

    def build_prompt(
        self,
        question: str,
        history: List[ChatMessage],
        retrieved_docs: List[Document],
    ) -> str:
        """Construct unified prompt string."""
        # 1. Format Context Blocks
        context_blocks = []
        if retrieved_docs:
            for idx, doc in enumerate(retrieved_docs, start=1):
                content = doc.page_content.strip() if hasattr(doc, "page_content") else str(doc).strip()
                context_blocks.append(f"[Document #{idx}]\n{content}")
            context_str = "\n\n".join(context_blocks)
        else:
            context_str = "No retrieved context available."

        # 2. Format History Block
        history_blocks = []
        if history:
            for msg in history[-6:]:  # Include last 3 turns (6 messages)
                role_str = "User" if msg.role == "user" else "Assistant"
                history_blocks.append(f"{role_str}: {msg.content}")
            history_str = "\n".join(history_blocks)
        else:
            history_str = "None"

        # 3. Assemble Unified Prompt
        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"=== PRIOR CONVERSATION HISTORY ===\n{history_str}\n\n"
            f"=== RETRIEVED CONTEXT DOCUMENTS ===\n{context_str}\n\n"
            f"=== CURRENT USER QUESTION ===\n{question}\n\n"
            f"ANSWER:"
        )

        logger.info(f"Built prompt (Length: {len(full_prompt)} chars, Context Docs: {len(retrieved_docs)})")
        return full_prompt
