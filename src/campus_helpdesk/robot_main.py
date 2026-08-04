"""Campus Helpdesk Robot – Production CLI Runtime Entry Point
==========================================================

Module: campus_helpdesk.robot_main
File:   src/campus_helpdesk/robot_main.py

Boots the physical robot runtime, loading settings from config.yaml/.env,
constructing real hardware services (Camera, Vision, VAD, STT, LLM GenerationRouter,
Piper TTS), wiring them into SystemRuntime, and monitoring signal interrupts for graceful shutdown.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.runtime.system_runtime import SystemRuntime

from campus_helpdesk.services.camera_service import CameraService
from campus_helpdesk.services.vision_service import VisionService
from campus_helpdesk.services.vad_service import VADService
from campus_helpdesk.services.stt_service import STTService, FasterWhisperBackend, MockTranscriptionBackend
from campus_helpdesk.services.inference_adapter import InferenceAdapter, LocalRAGBackend, MockInferenceBackend
from campus_helpdesk.services.tts_service import TTSService, PiperBackend, MockSpeechBackend

from campus_helpdesk.application.rag_chat_service import RAGChatService, DEFAULT_SYSTEM_PROMPT
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.llm.factory import create_llm_service

logger = logging.getLogger(__name__)


def build_production_runtime(
    use_mock: bool = False,
    camera_index: int | None = None,
    mic_index: int | None = None,
    speaker_index: int | None = None,
) -> SystemRuntime:
    """Construct a production-grade SystemRuntime instance wired with configured backends."""
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info("Initializing Campus Helpdesk Robot Runtime...")
    logger.info("Application: %s v%s (Environment: %s)", settings.app_name, settings.app_version, settings.app_env)

    bus = EventBus(maxsize=2000, max_workers=8, name="system-bus")

    # Camera & Vision Services
    cam_idx = camera_index if camera_index is not None else settings.webcam_index
    camera = CameraService(
        event_bus=bus,
        camera_index=cam_idx,
        fps=settings.camera_fps,
        use_mock_fallback=use_mock,
    )
    from campus_helpdesk.services.vision_service import MockPersonDetector
    vision_detector = MockPersonDetector() if use_mock else None
    vision = VisionService(event_bus=bus, detector=vision_detector)

    # Audio VAD Service
    m_idx = mic_index if mic_index is not None else settings.mic_device_index
    vad = VADService(
        event_bus=bus,
        device_index=m_idx if m_idx is not None else 0,
        use_mock_fallback=use_mock,
    )

    # STT Service
    stt_backend: Any
    if use_mock:
        stt_backend = MockTranscriptionBackend()
    else:
        stt_backend = FasterWhisperBackend(
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    stt = STTService(event_bus=bus, backend=stt_backend)

    # Inference Adapter & RAG Chat Service
    inference_backend: Any
    if use_mock:
        inference_backend = MockInferenceBackend()
    else:
        configured_llm = create_llm_service(settings)
        rag_pipeline = create_rag_pipeline(settings)
        if settings.faiss_index_path.exists():
            try:
                rag_pipeline.load_index()
            except Exception as exc:
                logger.warning("FAISS index load warning: %s", exc)

        session_mgr = SessionManager()
        query_rw = QueryRewriter()
        confidence_eng = ConfidenceEngine()
        answerability_eng = AnswerabilityEngine()
        context_builder = PromptContextBuilder(
            max_context_size=7000,
            similarity_threshold=settings.rag_distance_threshold,
        )

        from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
        context_composer = ContextComposer(settings=settings)

        chat_service = RAGChatService(
            llm_service=configured_llm,
            rag_pipeline=rag_pipeline,
            query_rewriter=query_rw,
            context_builder=context_builder,
            session_manager=session_mgr,
            confidence_engine=confidence_eng,
            answerability_engine=answerability_eng,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            context_composer=context_composer,
        )
        inference_backend = LocalRAGBackend(chat_service=chat_service)

    inference = InferenceAdapter(event_bus=bus, backend=inference_backend)

    # TTS Service
    spk_idx = speaker_index if speaker_index is not None else settings.speaker_device_index
    tts_backend: Any
    if use_mock:
        tts_backend = MockSpeechBackend()
    else:
        tts_backend = PiperBackend(
            model_path=settings.tts_voice_model,
            output_device=spk_idx,
        )
    tts = TTSService(event_bus=bus, backend=tts_backend)

    runtime = SystemRuntime(
        event_bus=bus,
        camera=camera,
        vision=vision,
        vad=vad,
        stt=stt,
        inference=inference,
        tts=tts,
    )
    return runtime


def main() -> None:
    """CLI launcher entry point."""
    parser = argparse.ArgumentParser(description="Campus Helpdesk Robot Runtime Launcher")
    parser.add_argument("--mock", action="store_true", help="Run with mock hardware backends")
    parser.add_argument("--camera-index", type=int, help="Override system camera index")
    parser.add_argument("--mic-index", type=int, help="Override USB microphone device index")
    parser.add_argument("--speaker-index", type=int, help="Override speaker device index")
    args = parser.parse_args()

    runtime = build_production_runtime(
        use_mock=args.mock,
        camera_index=args.camera_index,
        mic_index=args.mic_index,
        speaker_index=args.speaker_index,
    )

    def handle_signal(sig, frame):
        logger.info("Signal %d received; initiating graceful runtime shutdown...", sig)
        runtime.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting SystemRuntime...")
    runtime.start()
    logger.info("Robot runtime is fully active. Press Ctrl+C to stop.")

    try:
        while runtime.is_running():
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received; stopping runtime...")
    finally:
        runtime.stop()
        logger.info("Robot runtime shutdown complete.")


if __name__ == "__main__":
    main()
