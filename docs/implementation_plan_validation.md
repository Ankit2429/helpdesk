# Response Validation & Citation Engine Implementation Plan

## Architecture Overview

```mermaid
flowchart LR
    subgraph UI[User Interface]
        U[User]
    end
    subgraph CM[Conversation Manager]
        CMgr[ConversationManager]
    end
    subgraph QUP[Query Understanding]
        QUP[QueryUnderstandingPipeline]
    end
    subgraph RAG[Retrieval & Ranking]
        RAGPipe[RAGPipeline]
        CE[CrossEncoder]
    end
    subgraph LLM[Local LLM]
        LLM[Qwen (Ollama)]
    end
    subgraph VAL[Response Validation]
        RV[ResponseValidator]
        GND[GroundingChecker]
        CIT[CitationFormatter]
        CONF[ConfidenceEstimator]
        HALL[HallucinationDetector]
        POST[AnswerPostprocessor]
    end
    U --> CMgr --> QUP --> RAGPipe --> CE --> LLM --> RV
    RV --> GND --> CIT --> CONF --> POST
    POST --> U
```

## Component Responsibilities

| Component | Role |
|-----------|------|
| **ResponseValidator** | Orchestrates validation steps: grounding check, hallucination detection, confidence estimation, citation generation, and post‑processing. Returns the final answer.
| **GroundingChecker** | Splits LLM output into sentences, matches each sentence against retrieved chunks, labels as `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `UNSUPPORTED`.
| **CitationFormatter** | For each supported sentence, selects the most relevant chunk(s) and creates a citation string using metadata (document name, section, heading, page). Formats according to `citation_style`.
| **ConfidenceEstimator** | Aggregates retrieval similarity scores, cross‑encoder scores, number of supporting chunks, and grounding labels to produce a normalized confidence score (0‑1).
| **HallucinationDetector** | Applies heuristic rules / lightweight NER to detect fabricated entities (faculty names, locations, timings, fees). Flags sentences as hallucinations.
| **AnswerPostprocessor** | Removes or rewrites unsupported sentences, merges overlapping evidence, de‑duplicates content, and ensures readability while preserving citations.

## Data Flow (per request)
1. **ConversationManager** provides enriched query to **RAGPipeline**.
2. **RAGPipeline** returns ranked chunks and cross‑encoder scores.
3. **LLM** generates raw answer.
4. **ResponseValidator** receives raw answer + retrieved chunks.
   - **GroundingChecker** labels each sentence.
   - **HallucinationDetector** flags likely fabrications.
   - **CitationFormatter** attaches citations to supported sentences.
   - **ConfidenceEstimator** computes overall confidence.
   - **AnswerPostprocessor** removes/rewrites unsupported or hallucinated content, merges overlapping evidence, and formats final answer.
5. If confidence < `confidence_threshold` (or many unsupported sentences), **AnswerPostprocessor** substitutes a fallback message from `fallback_templates`.
6. Final answer is returned to the user.

## Grounding Check Algorithm
- Split LLM answer into sentences (use `nltk.sent_tokenize` or simple regex). 
- For each sentence, compute TF‑IDF / embedding similarity to each retrieved chunk.
- If similarity > `minimum_similarity_score` **and** cross‑encoder score > `minimum_cross_encoder_score` → `SUPPORTED`.
- If similarity between thresholds → `PARTIALLY_SUPPORTED`.
- Otherwise → `UNSUPPORTED`.
- Keep top‑k matching chunks per sentence for citation.

## Citation Generation Strategy
1. Select the highest‑scoring supporting chunk(s).
2. Extract metadata fields (`document_name`, `section`, `heading`, `page`).
3. Format according to `citation_style` (e.g., "[1] Document → Section").
4. Append citation inline (e.g., "... open from 9 AM to 8 PM[1].").
5. Maintain a citation index to avoid duplicate numbers.

## Confidence Estimation Formula (example)
```
confidence =
    w1 * avg_retrieval_similarity +
    w2 * avg_cross_encoder_score +
    w3 * (supported_sentences / total_sentences) +
    w4 * (1 - hallucination_ratio)
```
Weights (`w1..w4`) configurable in `validation.yaml` and normalized to sum to 1.
Result is clipped to [0,1].

## Hallucination Detection Heuristics
- **Entity List Checks**: Verify any named entity (faculty, department, building) appears in the retrieved metadata set.
- **Pattern Rules**: Detect improbable patterns like "the 3rd floor of the library" when no chunk mentions floor information.
- **Numeric Consistency**: Compare extracted numbers (fees, timings) against retrieved values; large discrepancy flags hallucination.

## Post‑Processing Steps
1. Remove `UNSUPPORTED` sentences (or replace with "I could not verify this information.").
2. Collapse consecutive sentences that share the same citation into a single paragraph.
3. De‑duplicate repeated facts.
4. Ensure proper punctuation and capitalize first word of each sentence.
5. Append a confidence footer if configured (e.g., "Confidence: 0.87").

## Raspberry Pi Considerations
- Use pure‑Python libraries only (`re`, `statistics`, optional `numpy` for vector ops).
- Embed small pre‑computed TF‑IDF vectors for chunks; avoid on‑device embedding models.
- Keep memory usage low: store only top‑k chunks (e.g., 10) for grounding.
- All configuration loaded once at start; caching of citation indexes.
- Aim for < 150 ms overhead per validation step.

## Configuration (`config/validation.yaml`)
```yaml
confidence_threshold: 0.6
minimum_cross_encoder_score: 0.7
minimum_similarity_score: 0.5
citation_style: "numeric"  # options: numeric, author_year
fallback_templates:
  low_confidence: "I couldn't find reliable information about that in the available campus documents."
  no_grounding: "I'm not sure about that; could you rephrase or ask about something else?"
weights:
  retrieval_similarity: 0.3
  cross_encoder: 0.3
  grounding: 0.2
  hallucination_penalty: 0.2
```

## File Structure
```
src/campus_helpdesk/
│
├─ validation/
│   ├─ __init__.py
│   ├─ response_validator.py      # main orchestrator
│   ├─ grounding_checker.py
│   ├─ citation_formatter.py
│   ├─ confidence_estimator.py
│   ├─ hallucination_detector.py
│   └─ answer_postprocessor.py
│
├─ config/
│   └─ validation.yaml
│
└─ evaluation/
    └─ response_validation_benchmark.py
```

## Evaluation Plan (`evaluation/response_validation_benchmark.py`)
- Load a held‑out set of queries with ground‑truth citations.
- Run the full pipeline with and without validation.
- Metrics:
  - **Grounding Accuracy**: % of sentences correctly labeled as supported.
  - **Citation Coverage**: % of supported sentences that have a citation.
  - **Unsupported Rate**: proportion of sentences removed.
  - **Hallucination Rate**: false positives detected.
  - **Fallback Accuracy**: correctness of fallback messages.
  - **Latency Overhead**: average additional time added by validation.
- Produce `evaluation/reports/validation_report.md` summarizing results.

## Logging
For each request log:
- Query and retrieved chunk IDs.
- Sentence‑level grounding labels.
- Detected hallucinations.
- Generated citations.
- Overall confidence score.
- Any fallback activation.
Logs written via the project's existing logging configuration.

## Open Design Questions
- **Similarity Metric**: Use cosine similarity on TF‑IDF vectors vs. lightweight dense embeddings? Trade‑off between accuracy and Pi resources.
- **Citation Style Flexibility**: Numeric vs. author‑year; need to support markdown footnotes?
- **Hallucination Rules vs. Model**: Should we incorporate a tiny language‑model‑based detector for better coverage?
- **Fallback Granularity**: Should we suggest alternative topics dynamically based on retrieved docs?
- **Evaluation Ground Truth**: Availability of manually annotated citations for training/evaluation.

---
### Next Steps
1. Review the implementation plan and answer the open questions.
2. Upon approval, create the package files and implement each component.
3. Add unit tests and the benchmark script.

*Please approve or provide feedback.*
