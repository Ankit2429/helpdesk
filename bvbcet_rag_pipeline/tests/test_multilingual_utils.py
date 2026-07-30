"""Unit tests for multilingual utilities."""

from utils.multilingual_utils import (
    detect_language,
    normalize_text,
    select_model_for_language,
)


def test_detect_language():
    lang_en, score_en = detect_language("What courses are offered in Computer Science?")
    assert lang_en == "en"
    assert score_en >= 0.50

    lang_kn, score_kn = detect_language("ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಕೋರ್ಸ್‌ಗಳು ಯಾವುವು?")
    assert lang_kn == "kn"
    assert score_kn >= 0.60

    lang_hi, score_hi = detect_language("कंप्यूटर साइंस में कौन से कोर्स हैं?")
    assert lang_hi == "hi"
    assert score_hi >= 0.60


def test_normalize_text():
    raw_text = "Café & Résumé   with   extra   spaces\u0301"
    normalized = normalize_text(raw_text, remove_diacritics=True)
    assert "Cafe" in normalized or "Cafe" in normalized
    assert "  " not in normalized


def test_select_model_for_language():
    model_en = select_model_for_language("en")
    assert model_en == "all-MiniLM-L6-v2"

    model_kn = select_model_for_language("kn")
    assert model_kn == "intfloat/multilingual-e5-base"
