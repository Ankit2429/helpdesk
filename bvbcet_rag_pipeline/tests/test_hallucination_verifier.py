"""Unit tests for Hallucination Verifier."""

from conversation_manager.hallucination_verifier import ClaimVerificationResult, HallucinationVerifier


def test_hallucination_verifier_grounded():
    verifier = HallucinationVerifier(grounding_threshold=0.30)

    query = "Where is CS department?"
    answer = "Computer Science department is located in B-Block."
    chunks = [{"text": "The Department of Computer Science and Engineering is located in B-Block building."}]

    res = verifier.verify_response(question=query, generated_answer=answer, retrieved_chunks=chunks)

    assert isinstance(res, ClaimVerificationResult)
    assert res.is_grounded is True
    assert len(res.flagged_sentences) == 0


def test_hallucination_verifier_ungrounded_flag():
    verifier = HallucinationVerifier(grounding_threshold=0.30)

    query = "What is the fee?"
    answer = "The tuition fee is 9999999 USD per semester."
    chunks = [{"text": "KCET quota fees are 125000 INR per academic year."}]

    res = verifier.verify_response(question=query, generated_answer=answer, retrieved_chunks=chunks)

    assert res.is_grounded is False
    assert len(res.flagged_sentences) == 1
