"""
Prompt Manager

Responsible for creating prompts that are sent to the LLM.
"""

from typing import List


class PromptManager:
    """
    Creates prompts for different conversation scenarios.
    """

    def __init__(self):
        self.system_prompt = """
You are CampusBot, an offline AI campus helpdesk assistant.

Your responsibilities:
- Answer only using the provided campus information.
- If the answer is not available in the provided context, say:
  "I'm sorry, I couldn't find that information in the campus documents."
- Never invent information.
- Keep answers concise, accurate, and polite.
- If asked unrelated questions, politely redirect the user to campus-related topics.
"""

    def build_rag_prompt(
        self,
        user_question: str,
        retrieved_context: List[str]
    ) -> str:
        """
        Builds a Retrieval-Augmented Generation (RAG) prompt.
        """

        context = "\n\n".join(retrieved_context)

        prompt = f"""
{self.system_prompt}

=========================
Campus Information
=========================
{context}

=========================
User Question
=========================
{user_question}

=========================
Assistant
=========================
"""

        return prompt.strip()

    def build_general_prompt(self, user_question: str) -> str:
        """
        Builds a prompt when no document context is available.
        """

        prompt = f"""
{self.system_prompt}

User:
{user_question}

Assistant:
"""

        return prompt.strip()