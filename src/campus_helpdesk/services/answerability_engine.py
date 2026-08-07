import logging

logger = logging.getLogger(__name__)

class AnswerabilityEngine:
    """Evaluates whether the retrieved context contains sufficient evidence to answer the query."""

    @staticmethod
    def evaluate_answerability(query: str, contexts: list[dict], confidence_level: str) -> str:
        """Evaluate context sufficiency. Returns: 'Supported', 'Partial', or 'Insufficient'."""
        if not contexts or confidence_level == "LOW":
            return "Insufficient"
            
        query_lower = query.lower()
        
        # Simple entity/keyword overlap check across contexts
        # Check if the query targets specific keywords (e.g. fees, hours, anti-ragging)
        important_keywords = ["fee", "fees", "rules", "hour", "time", "committee", "scholarship", "chancellor"]
        targeted_keywords = [kw for kw in important_keywords if kw in query_lower]
        
        high_confidence = confidence_level in {"HIGH", "VERY HIGH"}
        if not targeted_keywords:
            # Query is general
            return "Supported" if high_confidence else "Partial"
            
        # Match keywords in the retrieved context
        matches = 0
        context_body = " ".join([getattr(c, "content", "") for c in contexts]).lower()
        
        for kw in targeted_keywords:
            if kw in context_body:
                matches += 1
                
        if matches == len(targeted_keywords):
            return "Supported" if high_confidence else "Partial"
        elif matches > 0:
            return "Partial"
        else:
            return "Insufficient"
