import logging
import re

logger = logging.getLogger(__name__)

class CitationValidator:
    """Verifies that generated citations exist in the retrieved context and strips fabricated ones."""

    @staticmethod
    def validate_citations(response: str, contexts: list[dict]) -> str:
        """Scan response text, detect citation brackets (e.g. [1]), and validate against context array.
        
        Removes citation brackets that reference out-of-bounds indices.
        """
        # Find all patterns like [1], [2], [10]
        citations = re.findall(r"\[(\d+)\]", response)
        
        num_contexts = len(contexts)
        
        cleaned_response = response
        
        for cit in citations:
            cit_idx = int(cit)
            if cit_idx < 1 or cit_idx > num_contexts:
                # Fabricated or out of bounds citation
                logger.warning(f"Detected fabricated/invalid citation index: [{cit_idx}] (Context count: {num_contexts})")
                # Remove occurrences of [cit_idx] from response
                cleaned_response = re.sub(rf"\s*\[{cit_idx}\]", "", cleaned_response)
                
        # Also clean up generated URLs that do not match the cited document URLs
        # Extract URLs
        response_urls = re.findall(r"https?://[^\s)\]]+", cleaned_response)
        context_urls = {c.metadata.get("source_url", "") for c in contexts if c.metadata.get("source_url")}
        
        for url in response_urls:
            # Strip trailing punctuation from URL regex matches
            url_clean = url.rstrip(".,;)")
            if url_clean not in context_urls:
                logger.warning(f"Detected fabricated URL in response: {url_clean}")
                # Remove invalid URL from text
                cleaned_response = cleaned_response.replace(url, "")
                
        return cleaned_response
