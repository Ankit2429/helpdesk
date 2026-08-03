"""Full Trilingual End-to-End Voice Pipeline Test (STT/Text -> RAG Chat -> Multi-Voice TTS)."""

import logging
import os
import sys
from pathlib import Path
import wave
import numpy as np

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService, STTResult
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)
from campus_helpdesk.services.language_detector import LanguageDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_full_voice_pipeline")

OUTPUTS_DIR = Path("outputs")

TEST_INPUTS = [
    {
        "lang_code": "en",
        "language_name": "English",
        "text": "What is the fee structure for BE courses?",
    },
    {
        "lang_code": "hi",
        "language_name": "Hindi",
        "text": "बीई पाठ्यक्रम की फीस कितनी है?",
    },
    {
        "lang_code": "kn",
        "language_name": "Kannada",
        "text": "ಬಿಸಿಎ ಕೋರ್ಸ್‌ಗೆ ಸೇರಲು ಪ್ರವೇಶ ಅರ್ಹತೆಗಳು ಯಾವುವು?",
    },
]


def convert_wav_to_16k_mono_pcm(wav_path: Path) -> bytes:
    """Read a WAV file and convert to 16kHz 16-bit mono PCM bytes for STT processing."""
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    samples = np.frombuffer(raw_bytes, dtype=np.int16)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    if framerate != 16000:
        num_target_samples = int(len(samples) * 16000 / framerate)
        samples = np.interp(
            np.linspace(0, len(samples), num_target_samples, endpoint=False),
            np.arange(len(samples)),
            samples,
        ).astype(np.int16)

    return samples.tobytes()


def save_tts_response_to_wav(text: str, language: str, output_path: Path, tts_service: NonBlockingTTSService) -> None:
    """Render TTS speech output to a WAV file using Piper or pyttsx3 synthesis."""
    if output_path.exists():
        try:
            output_path.unlink()
        except Exception:
            pass

    voice_model_map = {"en": "en_US-lessac-medium", "hi": "hi_IN-pratham-medium"}
    model_name = voice_model_map.get(language)

    if model_name:
        voice = tts_service._load_piper_voice(model_name)
        if voice:
            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
            return

    import pyttsx3
    engine = pyttsx3.init()
    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    engine.stop()


def process_pipeline_turn(
    input_item: dict,
    chat_service: RAGChatService,
    stt_service: FasterWhisperSTTService,
    tts_service: NonBlockingTTSService,
    turn_idx: int,
) -> dict:
    """Process a single turn through the full pipeline: Input -> Detection -> RAG Chat -> Voice Output."""
    text_input = input_item.get("text")
    audio_input_path = input_item.get("audio_path")

    # Step 1: Input Processing & Language Detection
    if audio_input_path and Path(audio_input_path).exists():
        pcm_bytes = convert_wav_to_16k_mono_pcm(Path(audio_input_path))
        stt_result: STTResult = stt_service.transcribe_audio(pcm_bytes, sample_rate=16000)
        query_text = stt_result.text
        detected_lang = stt_result.language
        input_source_type = "Audio File (STT)"
    else:
        query_text = text_input
        detection = LanguageDetector.detect(query_text)
        detected_lang = detection.language
        input_source_type = "Text / Simulated STT"

    # Step 2: RAG Retrieval & LLM Generation in Detected Language
    chat_result = chat_service.respond(query_text, session_id="full_pipeline_session")

    # Step 3: Multi-Voice TTS Synthesis & Audio Artifact Preservation
    tts_service.speak(chat_result.reply, language=chat_result.detected_language)
    tts_service.wait_until_done(timeout=10.0)

    out_filename = f"full_pipeline_{chat_result.detected_language}_q{turn_idx}.wav"
    output_audio_path = OUTPUTS_DIR / out_filename
    save_tts_response_to_wav(chat_result.reply, chat_result.detected_language, output_audio_path, tts_service)

    return {
        "turn": turn_idx,
        "input_source_type": input_source_type,
        "question": query_text,
        "detected_language": chat_result.detected_language,
        "retrieved_sources": chat_result.supporting_sources,
        "text_answer": chat_result.reply,
        "audio_file_path": str(output_audio_path),
        "audio_file_size": output_audio_path.stat().st_size if output_audio_path.exists() else 0,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    OUTPUTS_DIR.mkdir(exist_ok=True)
    settings = get_settings()
    configure_logging("WARNING")

    print("\n" + "=" * 80)
    print("STARTING FULL TRILINGUAL END-TO-END VOICE PIPELINE TEST")
    print("========================================================================")

    # 1. Initialize Embeddings & Vector Store
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=settings.embedding_show_progress,
        local_files_only=settings.embedding_local_files_only,
    )
    similarity_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=settings.faiss_index_path,
        allow_dangerous_deserialization=settings.faiss_allow_dangerous_deserialization,
        embedding_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )
    markdown_loader = MarkdownKnowledgeLoader(
        knowledge_source_path=settings.knowledge_source_path,
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )
    text_chunker = SemanticDocumentChunker(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=settings.rag_chunk_separators,
        add_start_index=settings.rag_add_start_index,
    )
    rag_pipeline = RAGPipeline(
        document_loader=markdown_loader,
        document_chunker=text_chunker,
        similarity_store=similarity_store,
        search_limit=settings.rag_search_limit,
    )
    if settings.faiss_index_path.exists():
        rag_pipeline.load_index()

    # 2. Initialize LLM, STT, and TTS Services
    llm_service = OllamaLLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        generation_options=settings.ollama_options,
    )
    chat_service = RAGChatService(llm_service=llm_service, rag_pipeline=rag_pipeline)
    stt_service = FasterWhisperSTTService(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    tts_service = NonBlockingTTSService(piper_models_dir=settings.tts_piper_models_dir)

    print("\n[Pipeline Services Initialized Successfully]")
    print("-" * 80 + "\n")

    # 3. Process Turns for English, Hindi, and Kannada
    for idx, input_item in enumerate(TEST_INPUTS, start=1):
        res = process_pipeline_turn(input_item, chat_service, stt_service, tts_service, idx)

        lang_name = input_item["language_name"]
        print(f"--- Turn #{res['turn']}: {lang_name} ({res['detected_language'].upper()}) ---")
        print(f"Input Type          : {res['input_source_type']}")
        print(f"User Question       : \"{res['question']}\"")
        print(f"Detected Language   : '{res['detected_language']}' ({lang_name})")
        print(f"Generated Text Reply: \"{res['text_answer']}\"")
        print("Retrieved Sources   :")
        for src in res["retrieved_sources"]:
            print(f"  - {src}")
        print(f"Saved Response Audio: {res['audio_file_path']} ({res['audio_file_size']} bytes / {res['audio_file_size']/1024:.2f} KB)")
        print("-" * 80 + "\n")


if __name__ == "__main__":
    main()
