"""Wake Word Service.

Provides event-driven wake word detection integrated with Campus Helpdesk EventBus.
"""

from __future__ import annotations

import logging
import threading
import wave
from typing import Optional

from campus_helpdesk.infrastructure.audio.wake_word import WakeWordDetector
from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import EventEnvelope, EventType

logger = logging.getLogger(__name__)


class WakeWordService:
    """Service wrapping WakeWordDetector and emitting WAKE_WORD_DETECTED events onto EventBus."""

    def __init__(
        self,
        event_bus: EventBus,
        wake_phrase: str = "Hey Helpdesk",
        sensitivity: float = 0.5,
        device_index: Optional[int] = None,
        on_wake_detected: Optional[Callable[[], None]] = None,
    ) -> None:
        self.event_bus = event_bus
        self.wake_phrase = wake_phrase
        self.on_wake_detected_cb = on_wake_detected
        self.detector = WakeWordDetector(
            wake_phrase=wake_phrase,
            sensitivity=sensitivity,
            device_index=device_index,
            on_wake_detected=self._handle_wake,
        )
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start wake word service."""
        logger.info("Starting WakeWordService with wake phrase '%s'...", self.wake_phrase)
        self.detector.start()

    def stop(self) -> None:
        """Stop wake word service."""
        logger.info("Stopping WakeWordService...")
        self.detector.stop()

    def is_running(self) -> bool:
        """Check if service is actively listening."""
        return self.detector.is_running()

    def _handle_wake(self) -> None:
        """Callback invoked when wake word is detected."""
        logger.info("[WakeWordService] Wake word '%s' detected! Emitting event.", self.wake_phrase)
        try:
            event = EventEnvelope(
                event_type=EventType.USER_APPROACHED,  # Wake word triggers robot interaction
                payload={"wake_phrase": self.wake_phrase, "source": "wake_word_service"},
            )
            self.event_bus.publish(event)
        except Exception as exc:
            logger.error("[WakeWordService] Error publishing wake event: %s", exc, exc_info=True)

        if self.on_wake_detected_cb:
            try:
                self.on_wake_detected_cb()
            except Exception as exc:
                logger.error("[WakeWordService] Error in on_wake_detected_cb: %s", exc, exc_info=True)
