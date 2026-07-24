"""
RAG Service

Coordinates the Retrieval-Augmented Generation (RAG) pipeline.

Pipeline:
Question
    ↓
Retriever
    ↓
Relevant Context
    ↓
Prompt Manager
    ↓
Ollama
    ↓
Response Parser
"""

from typing import List

from campus_helpdesk.infrastructure.rag.retriever import Retriever
from campus_helpdesk.infrastructure.llm.prompt_manager import PromptManager
from campus_helpdesk.infrastructure.llm.ollama_client import OllamaClient
from campus_helpdesk.infrastructure.llm.response_parser import ResponseParser


class RagService:
    """
    Main service responsible for answering user questions using RAG.
    """

    def __init__(
        self,
        retriever: Retriever,
        ollama_client: OllamaClient,
        prompt_manager: PromptManager,
        response_parser: ResponseParser,
    ):
        self.retriever = retriever
        self.ollama_client = ollama_client
        self.prompt_manager = prompt_manager
        self.response_parser = response_parser

    def ask(self, question: str) -> str:
        """
        Answers a question using the RAG pipeline.
        """

        # Retrieve relevant chunks
        context_chunks: List[str] = self.retriever.retrieve(question)

        # Build prompt
        prompt = self.prompt_manager.build_rag_prompt(
            user_question=question,
            retrieved_context=context_chunks,
        )

        # Generate response
        raw_response = self.ollama_client.generate(prompt)

        # Clean response
        final_response = self.response_parser.parse(raw_response)

        return final_response