"""Unit tests for Citation Formatter."""

from retrieval.citation_formatter import Citation, CitationFormatter, FormattedCitationOutput


def test_citation_formatter():
    dummy_chunks = [
        {
            "text": "The Computer Science Department is located in B-Block.",
            "score": 0.88,
            "metadata": {
                "source": "computer_science.md",
                "relative_path": "markdown/departments/computer_science.md",
                "heading": "Location",
                "level": 2,
                "page_number": 3,
            },
        }
    ]

    result = CitationFormatter.format_citations(dummy_chunks, snippet_max_len=200)

    assert isinstance(result, FormattedCitationOutput)
    assert len(result.citations) == 1
    assert isinstance(result.citations[0], Citation)
    assert result.citations[0].source_doc == "computer_science.md"
    assert result.citations[0].page_number == 3
    assert result.citations[0].confidence_score > 0.0
    assert "computer_science.md" in result.formatted_citations_text
