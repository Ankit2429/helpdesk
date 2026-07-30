"""Unit tests for Response Trimmer and Filler Stripper."""

from conversation_manager.response_trimmer import QueryIntent, ResponseTrimmer, ResponseTrimmerOutput


def test_strip_preamble():
    raw_fluff = "Great question! As an AI assistant, Computer Science is located in B-Block."
    cleaned, filler_found = ResponseTrimmer.strip_preamble(raw_fluff)

    assert filler_found is True
    assert "Computer Science is located in B-Block." in cleaned
    assert "Great question!" not in cleaned


def test_process_response_length_trimming():
    long_response = (
        "Computer Science offers B.E. programs. "
        "Admissions start in July via KCET. "
        "Fees are 125000 INR per year. "
        "Placement stats are high. "
        "Hostel facilities are available for outstation students."
    )

    result = ResponseTrimmer.process_response(
        raw_response=long_response,
        query="What is the admission procedure?",
        max_sentences=3,
    )

    assert isinstance(result, ResponseTrimmerOutput)
    assert result.query_intent == QueryIntent.FACTUAL_QUICK
    assert result.final_sentence_count <= 3
