"""Conversation Manager.

Orchestrates the voice assistant lifecycle state machine:
  IDLE -> WAKE_WORD_DETECTED -> LISTENING -> THINKING -> SPEAKING -> IDLE

Features:
- Maintains multi-turn conversation memory.
- Handles silence timeouts.
- Manages barge-in (interruption): when the user starts speaking while the assistant is in SPEAKING state,
  instantly cancels TTS playback, cancels LLM generation, and switches directly to LISTENING state.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import EventEnvelope, EventType

logger = logging.getLogger(__name__)


class AssistantState(enum.Enum):
    """Voice Assistant Operational States."""
    READY = "ready"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class ConversationManager:
    """Orchestrates end-to-end voice pipeline execution and state transitions.

    Parameters
    ----------
    chat_service:
        RAGChatService instance for RAG retrieval and LLM response streaming.
    stt_service:
        FasterWhisperSTTService instance for streaming STT transcription.
    tts_service:
        NonBlockingTTSService instance for sentence-level TTS synthesis.
    event_bus:
        Optional EventBus to publish state change events.
    on_state_changed:
        Optional UI callback for state visual indicator updates (state, text).
    on_transcript_updated:
        Optional UI callback for live streaming partial transcript updates (text, is_final).
    """

    def __init__(
        self,
        chat_service: Optional[RAGChatService] = None,
        stt_service: Optional[FasterWhisperSTTService] = None,
        tts_service: Optional[NonBlockingTTSService] = None,
        event_bus: Optional[EventBus] = None,
        on_state_changed: Optional[Callable[[AssistantState, str], None]] = None,
        on_transcript_updated: Optional[Callable[[str, bool], None]] = None,
        session_id: str = "voice-kiosk-session",
        max_history_turns: int = 5,
    ) -> None:
        self.chat_service = chat_service
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.event_bus = event_bus
        self.on_state_changed = on_state_changed
        self.on_transcript_updated = on_transcript_updated
        self.session_id = session_id
        self.max_history_turns = max_history_turns

        from campus_helpdesk.domain.memory.conversation_memory import ConversationMemory
        self._memory = ConversationMemory(max_history_turns=max_history_turns)

        self._state = AssistantState.IDLE
        self._lock = threading.Lock()
        self._stt_stop_event = threading.Event()
        self._generation_cancel_event = threading.Event()
        self._active_thread: Optional[threading.Thread] = None

    def add_user_message(self, content: str) -> None:
        """Add user message to conversation memory."""
        self._memory.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add assistant response to conversation memory."""
        self._memory.add_message("assistant", content)

    def get_recent_history(self):
        """Retrieve recent conversation history as ChatMessage instances."""
        from campus_helpdesk.domain.conversation import ChatMessage
        return [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in self._memory.get_messages()
        ]

    def reset_session(self, session_id: str = "default") -> None:
        """Clear conversation memory session."""
        self._memory.clear()

    @property
    def state(self) -> AssistantState:
        """Current assistant state."""
        with self._lock:
            return self._state

    def _set_state(self, new_state: AssistantState, message: str = "") -> None:
        """Set assistant state and trigger UI/event listeners."""
        with self._lock:
            old_state = self._state
            self._state = new_state

        logger.info("[ConversationManager] Transition: %s -> %s (%s)", old_state.value, new_state.value, message)

        if self.event_bus:
            try:
                from campus_helpdesk.interaction.events import SystemPayload
                self.event_bus.publish(
                    EventEnvelope(
                        event_type=EventType.SYSTEM_READY,
                        source="conversation_manager",
                        payload=SystemPayload(profile="touch_app", message=f"{old_state.value} -> {new_state.value}: {message}"),
                    )
                )
            except Exception as exc:
                logger.error("[ConversationManager] Error publishing state event: %s", exc)

        if self.on_state_changed:
            try:
                self.on_state_changed(new_state, message)
            except Exception as exc:
                logger.error("[ConversationManager] Error notifying state listener: %s", exc)

    def on_wake_word_triggered(self, wake_phrase: str = "Hey Helpdesk") -> None:
        """Invoked when wake word detector triggers. Transitions to LISTENING."""
        logger.info("[ConversationManager] Wake word triggered: '%s'", wake_phrase)

        # Barge-in: if currently speaking, interrupt TTS & LLM generation immediately
        if self.state in (AssistantState.SPEAKING, AssistantState.THINKING):
            self.cancel_speech_and_generation()

        self._set_state(AssistantState.LISTENING, f"Wake word '{wake_phrase}' detected. Listening...")

        # Play wake chime / TTS feedback non-blockingly
        if self.tts_service:
            self.tts_service.speak("How can I help you?", language="en")

        # Start streaming STT listening session in background thread
        self.start_listening_session()

    def cancel_speech_and_generation(self) -> None:
        """Instantly interrupt active TTS playback, LLM generation, and STT stream (Barge-in)."""
        logger.info("[ConversationManager] Barge-in / Interrupt requested! Canceling TTS and generation.")
        self._generation_cancel_event.set()
        self._stt_stop_event.set()
        if self.tts_service:
            self.tts_service.cancel_playback()

    def handle_user_speech_started(self) -> None:
        """Invoked when VAD detects user voice onset. Triggers barge-in if assistant is speaking."""
        current = self.state
        if current in (AssistantState.SPEAKING, AssistantState.THINKING):
            logger.info("[ConversationManager] User started speaking during %s! Triggering barge-in.", current.value)
            self.cancel_speech_and_generation()
            self.start_listening_session()

    def start_listening_session(self) -> None:
        """Launch background streaming STT session."""
        with self._lock:
            if self._active_thread and self._active_thread.is_alive():
                return

            self._stt_stop_event.clear()
            self._generation_cancel_event.clear()
            self._active_thread = threading.Thread(
                target=self._listening_loop,
                daemon=True,
                name="ConvMgr-listening_loop",
            )
            self._active_thread.start()

    def _listening_loop(self) -> None:
        """Execute STT streaming listener, automatic language detection, and RAG/LLM invocation."""
        final_transcript = ""
        detected_lang = "en"

        def _stt_callback(text: str, is_final: bool) -> None:
            nonlocal final_transcript
            if text:
                final_transcript = text
                if self.on_transcript_updated:
                    try:
                        self.on_transcript_updated(text, is_final)
                    except Exception as exc:
                        logger.error("[ConversationManager] Error updating transcript UI: %s", exc)

        try:
            # 1. Stream microphone audio and transcribe live
            if self.stt_service:
                self.stt_service.listen_and_transcribe_stream(
                    callback=_stt_callback,
                    stop_event=self._stt_stop_event,
                    tts_service=self.tts_service,
                )

            # Check if listening session was cancelled
            if self._stt_stop_event.is_set() and not final_transcript:
                self._set_state(AssistantState.IDLE, "Listening cancelled.")
                return

            if not final_transcript.strip():
                logger.info("[ConversationManager] No speech transcribed. Returning to IDLE.")
                self._set_state(AssistantState.IDLE, "No speech detected.")
                return

            # 2. Transition to THINKING state
            self._set_state(AssistantState.THINKING, f"Processing question: '{final_transcript}'")

            # Auto language detection is handled in RAGChatService / STTResult
            # 3. Stream RAG retrieval & local LLM response
            self._process_and_speak_response(final_transcript)

        except Exception as exc:
            logger.error("[ConversationManager] Error in listening loop: %s", exc, exc_info=True)
            self._set_state(AssistantState.IDLE, f"Error: {exc}")

    def _process_and_speak_response(self, query: str) -> None:
        """Query RAGChatService and stream answer tokens to TTS & UI."""
        self._set_state(AssistantState.THINKING, "Searching campus knowledge base...")

        try:
            if not self.chat_service or not self.tts_service:
                logger.warning("[ConversationManager] Chat or TTS service unavailable for response.")
                return

            # Get token stream generator from RAGChatService
            token_stream = self.chat_service.respond_stream(query, session_id=self.session_id)

            self._set_state(AssistantState.SPEAKING, "Streaming response...")

            # Hook token stream into sentence-level streaming TTS
            self.tts_service.speak_stream(token_stream, language="en")

            # Wait for TTS audio to complete playback
            self.tts_service.wait_until_done(timeout=20.0)

        except Exception as exc:
            logger.error("[ConversationManager] RAG/LLM streaming error: %s", exc, exc_info=True)

        finally:
            # Return to IDLE state once response completes
            self._set_state(AssistantState.IDLE, "Ready.")
