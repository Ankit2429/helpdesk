"""Language detection utility supporting Indic scripts and general text detection."""

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)


class DetectionResult(NamedTuple):
    language: str
    language_name: str
    confidence: float


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}


class LanguageDetector:
    """Detect language of user text queries via Unicode script analysis & langdetect fallback."""

    @staticmethod
    def detect(text: str) -> DetectionResult:
        if not text or not text.strip():
            return DetectionResult("en", "English", 1.0)

        # 1. Check Devanagari script range (Hindi)
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        if devanagari_chars > 0:
            return DetectionResult("hi", "Hindi", 0.99)

        # 2. Check Kannada script range (Kannada)
        kannada_chars = len(re.findall(r"[\u0C80-\u0CFF]", text))
        if kannada_chars > 0:
            return DetectionResult("kn", "Kannada", 0.99)

        # 3. Fallback to langdetect library for Latin / other scripts
        try:
            import langdetect

            lang_code = langdetect.detect(text).lower()
            if lang_code in ("hi", "kn", "en"):
                return DetectionResult(lang_code, LANGUAGE_NAMES.get(lang_code, "English"), 0.95)
            elif lang_code in ("mr", "ne"):
                return DetectionResult("hi", "Hindi", 0.90)
        except Exception:
            pass

        return DetectionResult("en", "English", 1.0)
