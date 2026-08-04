"""Touchscreen App Entry Point.

Launches the CustomTkinter touch UI (ChatView) wired directly to the real
RAGChatService — the same RAG/LLM pipeline used by the FastAPI /chat route
and by robot_main.py. No HTTP hop: the UI calls the service in-process,
which is the right choice for a kiosk running on the same Pi as the model.

Run with:
    uvicorn is NOT used here — this is a desktop/kiosk process, not the API.
    python -m campus_helpdesk.touch_app          (from src/, with venv active)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.application.rag_chat_service import DEFAULT_SYSTEM_PROMPT, RAGChatService
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.presentation.chat_view import ChatView
from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine

logger = logging.getLogger(__name__)


def create_stt_callback() -> Optional[Callable[[], str]]:
    """Initialize FasterWhisperSTTService push-to-talk callback if audio hardware/model is available."""
    try:
        from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService

        settings = get_settings()
        stt_service = FasterWhisperSTTService(
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            device_index=settings.mic_device_index,
        )
        logger.info("FasterWhisperSTTService initialized for touch UI push-to-talk.")
        return lambda: stt_service.listen_and_transcribe(timeout=8, phrase_time_limit=15)
    except Exception as exc:
        logger.warning("Could not initialize STT service for touch UI: %s", exc)
        return None
def build_chat_service() -> RAGChatService:
    """Wire RAGChatService exactly the way main.py / robot_main.py do."""
    settings = get_settings()
    configure_logging(settings.log_level)

    llm_service = create_llm_service(settings)
    rag_pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        try:
            rag_pipeline.load_index()
        except Exception as exc:
            logger.warning("Could not load FAISS index from %s: %s", settings.faiss_index_path, exc)

    context_builder = PromptContextBuilder(
        max_context_size=7000,
        similarity_threshold=settings.rag_distance_threshold,
    )
    context_composer = ContextComposer(settings=settings)

    service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        query_rewriter=QueryRewriter(),
        context_builder=context_builder,
        session_manager=SessionManager(),
        confidence_engine=ConfidenceEngine(),
        answerability_engine=AnswerabilityEngine(),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        context_composer=context_composer,
    )
    return service


def make_ask_callback(chat_service: RAGChatService, session_id: str = "touch-kiosk"):
    """Adapt RAGChatService.respond() -> the dict shape ChatView expects."""

    def ask(query: str, language: Optional[str] = None) -> Dict[str, Any]:
        prompt_query = query
        if language and language.lower() != "en":
            lang_code = language.lower()
            if lang_code == "kn":
                prefix = "Respond only in Kannada (ಕನ್ನಡ) script. "
            elif lang_code == "hi":
                prefix = "Respond only in Hindi (हिंदी) script. "
            elif lang_code == "hinglish":
                prefix = "Respond in Hinglish: a natural Hindi-English mix, written in Latin script. "
            elif lang_code == "kanglish":
                prefix = "Respond in Kanglish: a natural Kannada-English mix, written in Latin script. "
            else:
                prefix = f"Respond in {language}. "
            prompt_query = f"{prefix}{query}"

        result = chat_service.respond(prompt_query, session_id=session_id)
        
        sources = [
            {"source": s, "heading": "", "score": result.confidence_score}
            for s in result.supporting_sources
        ]
        return {
            "answer": result.reply,
            "sources": sources,
            "current_topic": result.confidence_level,
        }

    return ask

def create_tts_service() -> Optional[Any]:
    """Initialize NonBlockingTTSService for real-time speech synthesis if available."""
    try:
        from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService

        settings = get_settings()
        tts = NonBlockingTTSService(
            voice_model=settings.tts_voice_model,
            piper_models_dir=settings.tts_piper_models_dir,
            use_cuda=settings.tts_use_cuda,
        )
        logger.info("NonBlockingTTSService initialized for touch UI speech synthesis.")
        return tts
    except Exception as exc:
        logger.warning("Could not initialize TTS service for touch UI: %s", exc)
        return None


def make_ask_stream_callback(chat_service: RAGChatService, session_id: str = "touch-kiosk"):
    """Adapt RAGChatService.respond_stream() for token-by-token streaming."""

    def ask_stream(query: str, language: Optional[str] = None):
        prompt_query = query
        if language and language.lower() != "en":
            lang_code = language.lower()
            if lang_code == "kn":
                prefix = "Respond only in Kannada (ಕನ್ನಡ) script. "
            elif lang_code == "hi":
                prefix = "Respond only in Hindi (हिंदी) script. "
            elif lang_code == "hinglish":
                prefix = "Respond in Hinglish: a natural Hindi-English mix, written in Latin script. "
            elif lang_code == "kanglish":
                prefix = "Respond in Kanglish: a natural Kannada-English mix, written in Latin script. "
            else:
                prefix = f"Respond in {language}. "
            prompt_query = f"{prefix}{query}"

        def generator_wrapper():
            for token in chat_service.respond_stream(prompt_query, session_id=session_id):
                yield token

        return generator_wrapper()

    return ask_stream


class TouchApp(ctk.CTk):
    """Root kiosk window featuring dual-panel layout: ChatView on left, embedded CameraView on right."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Sparky — Campus Helpdesk Robot")
        self.attributes("-fullscreen", True)  # kiosk mode on touchscreen
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))  # dev toggle

        theme_engine = ThemeEngine(mode="dark")
        chat_service = build_chat_service()
        ask_callback = make_ask_callback(chat_service)
        ask_stream_callback = make_ask_stream_callback(chat_service)
        tts_service = create_tts_service()
        # Initialize single STT service instance
        self.stt_service: Optional[Any] = None
        try:
            from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
            settings = get_settings()
            self.stt_service = FasterWhisperSTTService(
                model_size=settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                device_index=settings.mic_device_index,
            )
            logger.info("FasterWhisperSTTService initialized for TouchApp.")
        except Exception as exc:
            logger.warning("Could not initialize STT service for TouchApp: %s", exc)

        def safe_stt_callback() -> str:
            if not self.stt_service:
                return ""
            was_wake_running = False
            if self.wake_service and hasattr(self.wake_service, "is_running") and self.wake_service.is_running():
                logger.info("[TouchApp] Pausing WakeWordService stream for push-to-talk recording...")
                try:
                    self.wake_service.stop()
                    was_wake_running = True
                except Exception as e:
                    logger.warning("[TouchApp] Error stopping wake service: %s", e)

            try:
                return self.stt_service.listen_and_transcribe(timeout=8, phrase_time_limit=15)
            finally:
                if was_wake_running and self.wake_service:
                    logger.info("[TouchApp] Resuming WakeWordService stream post push-to-talk...")
                    try:
                        self.wake_service.start()
                    except Exception as e:
                        logger.warning("[TouchApp] Error resuming wake service: %s", e)

        # Single-panel kiosk layout (ChatView full width)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Chat Interface Panel
        self.chat_view = ChatView(
            self,
            theme_engine=theme_engine,
            ask_callback=ask_callback,
            ask_stream_callback=ask_stream_callback,
            stt_callback=safe_stt_callback,
            tts_service=tts_service,
            on_language_changed=self._handle_language_changed,
        )
        self.chat_view.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        # 2. Wire ConversationManager & WakeWordService if audio services available
        self.conv_manager: Optional[Any] = None
        self.wake_service: Optional[Any] = None

        try:
            from campus_helpdesk.application.conversation_manager import ConversationManager
            from campus_helpdesk.services.wake_word_service import WakeWordService
            from campus_helpdesk.interaction.event_bus import EventBus

            bus = EventBus()
            if self.stt_service:
                self.conv_manager = ConversationManager(
                    chat_service=chat_service,
                    stt_service=self.stt_service,
                    tts_service=tts_service or create_tts_service(),
                    event_bus=bus,
                    on_state_changed=lambda st, msg: self.after(0, lambda: self.chat_view.update_voice_state(st.value, msg)),
                    on_transcript_updated=lambda txt, is_fin: self.after(0, lambda: self.chat_view.update_live_transcript(txt, is_fin)),
                )

            self.wake_service = WakeWordService(
                event_bus=bus,
                wake_phrase="Hey Campus",
                device_index=get_settings().mic_device_index,
            )
            self.wake_service.start()
            logger.info("TouchApp voice pipeline & WakeWordService initialized.")

        except Exception as exc:
            logger.warning("Could not initialize full voice pipeline in TouchApp: %s", exc)

    def _handle_greeting_triggered(self, greeting_text: str, language: str) -> None:
        """Forward greeting event from HRI intent engine to ChatView UI & TTS."""
        logger.info(f"[TouchApp Greeting Received] Text='{greeting_text}' (Language='{language}')")
        if hasattr(self, "chat_view"):
            self.chat_view.trigger_greeting(greeting_text, language)

    def _handle_language_changed(self, new_language: str) -> None:
        """Synchronize active language across ChatView, STT, LLM, TTS."""
        logger.info(f"[TouchApp Language Synchronized] New Language: '{new_language}'")


def main() -> None:
    app = TouchApp()
    app.mainloop()


if __name__ == "__main__":
    main()