"""Unit tests for Transliteration and Proper Noun preservation."""

from utils.transliteration_utils import LanguageAnalysisResult, TransliterationProcessor


def test_transliteration_processor_hinglish():
    res = TransliterationProcessor.analyze_turn_language("KCET fees kitna hai for B.E. Computer Science?")

    assert isinstance(res, LanguageAnalysisResult)
    assert res.primary_language == "hinglish"
    assert res.is_transliterated is True
    assert "KCET" in res.protected_nouns_found
    assert "B.E." in res.protected_nouns_found


def test_transliteration_processor_kanglish():
    res = TransliterationProcessor.analyze_turn_language("Admissions yelli aguthe and KCET process beku?")

    assert res.primary_language == "kanglish"
    assert res.is_transliterated is True
    assert "KCET" in res.protected_nouns_found


def test_preserve_proper_nouns():
    text = "The kcet counselling happens at kle tech campus."
    cleaned = TransliterationProcessor.preserve_proper_nouns(text, ["KCET", "KLE Tech"])

    assert "KCET" in cleaned
    assert "KLE Tech" in cleaned
