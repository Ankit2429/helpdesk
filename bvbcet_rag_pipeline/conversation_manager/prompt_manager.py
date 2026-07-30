"""Versioned System Prompt Management Engine.

Defines role-specific system prompts, persona constraints, length guidelines,
and grounding instructions. Supports prompt versioning (v1_baseline, v2_grounded_concise)
for A/B testing and eval benchmarking.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, Optional

from logger.logger import get_logger

logger = get_logger("prompt_manager")

V1_BASELINE_PROMPT = """You are an AI Campus Helpdesk Assistant for KLE Technological University (formerly BVBCET), Hubballi.

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


V2_GROUNDED_CONCISE_PROMPT = """You are the official AI Campus Helpdesk Assistant for KLE Technological University (formerly BVBCET), Hubballi.

Persona & Tone: Direct, polite, factual, concise. Never use filler phrases like "Great question!", "Sure!", or "As an AI assistant".

Constraints:
1. Grounding Rule: Answer strictly using ONLY the provided retrieved context. If the answer is not present in the context, reply EXACTLY:
   "I couldn't find that information in the college knowledge base."
2. Brevity Rule: Default to 2 to 4 concise sentences for factual queries. Avoid restating the question or adding conversational preamble.
3. Citation Rule: Present facts clearly without speculating or making assumptions outside the context.
4. Language Rule: Match the user's query language and preserve non-translatable proper nouns (KLE Tech, B.E., KCET, COMEDK, M.Tech, B-Block).

{conversation_summary_block}

Retrieved Knowledge Base Context:
--------------------------------------------------
{context}
--------------------------------------------------

User Question: {question}

Answer:"""


@dataclass
class PromptTemplateVersion:
    """Dataclass representing a versioned prompt template."""

    version_id: str
    description: str
    template_text: str


class SystemPromptManager:
    """Manages versioned system prompt templates and selection."""

    def __init__(self, default_version: str = "v2_grounded_concise") -> None:
        self.default_version = default_version
        self.prompts: Dict[str, PromptTemplateVersion] = {
            "v1_baseline": PromptTemplateVersion(
                version_id="v1_baseline",
                description="Original baseline RAG prompt",
                template_text=V1_BASELINE_PROMPT,
            ),
            "v2_grounded_concise": PromptTemplateVersion(
                version_id="v2_grounded_concise",
                description="Production concise grounded prompt with persona & filler constraints",
                template_text=V2_GROUNDED_CONCISE_PROMPT,
            ),
        }

    def get_prompt(self, version_id: Optional[str] = None) -> PromptTemplateVersion:
        """Get prompt template version instance."""
        target_v = version_id or self.default_version
        if target_v not in self.prompts:
            logger.warning(f"Prompt version '{target_v}' not found. Falling back to default '{self.default_version}'")
            target_v = self.default_version
        return self.prompts[target_v]

    def format_prompt(
        self,
        question: str,
        context_str: str,
        summary_block: str = "",
        version_id: Optional[str] = None,
    ) -> str:
        """Format complete prompt string for specified prompt version."""
        prompt_ver = self.get_prompt(version_id)
        return prompt_ver.template_text.format(
            conversation_summary_block=summary_block,
            context=context_str,
            question=question,
        )
