"""Pure Python Okapi BM25 sparse keyword search store for exact term matching."""

import math
import re
from collections import Counter
from collections.abc import Sequence

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult


class BM25SearchStore:
    """Okapi BM25 keyword search index for precise term matching."""

    TOKEN_PATTERN = re.compile(r"\w+")

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._documents: list[KnowledgeDocument] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_lens: list[int] = []
        self._avg_doc_len: float = 0.0
        self._doc_freqs: Counter[str] = Counter()
        self._total_docs: int = 0

    def tokenize(self, text: str) -> list[str]:
        """Lowercases and extracts word tokens from text."""
        return self.TOKEN_PATTERN.findall(text.lower())

    def index_documents(self, documents: Sequence[KnowledgeDocument]) -> None:
        """Build in-memory BM25 inverted index stats from KnowledgeDocuments."""
        self._documents = list(documents)
        self._doc_tokens = []
        self._doc_lens = []
        self._doc_freqs = Counter()
        self._total_docs = len(self._documents)

        if self._total_docs == 0:
            self._avg_doc_len = 0.0
            return

        total_len = 0
        for doc in self._documents:
            tokens = self.tokenize(doc.content)
            self._doc_tokens.append(tokens)
            doc_len = len(tokens)
            self._doc_lens.append(doc_len)
            total_len += doc_len

            unique_tokens = set(tokens)
            for t in unique_tokens:
                self._doc_freqs[t] += 1

        self._avg_doc_len = total_len / self._total_docs

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Perform Okapi BM25 keyword search for a query string."""
        if not query.strip() or self._total_docs == 0:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: list[float] = [0.0] * self._total_docs

        for token in query_tokens:
            doc_freq = self._doc_freqs.get(token, 0)
            if doc_freq == 0:
                continue

            # Inverse Document Frequency (IDF) using Lucene/Okapi formula
            idf = math.log(1.0 + (self._total_docs - doc_freq + 0.5) / (doc_freq + 0.5))

            for idx in range(self._total_docs):
                tokens = self._doc_tokens[idx]
                if not tokens:
                    continue
                term_freq = tokens.count(token)
                if term_freq == 0:
                    continue

                doc_len = self._doc_lens[idx]
                numerator = term_freq * (self.k1 + 1.0)
                denominator = term_freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self._avg_doc_len))

                scores[idx] += idf * (numerator / denominator)

        # Pair scores with documents and sort descending
        scored_docs = [
            (scores[i], self._documents[i])
            for i in range(self._total_docs)
            if scores[i] > 0.0
        ]
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        top_matches = scored_docs[:limit]
        return [
            SearchResult(
                document=doc,
                # Convert BM25 score to pseudo distance (1 / (1 + score)) for interface uniformity
                distance=round(1.0 / (1.0 + score), 4),
            )
            for score, doc in top_matches
        ]
