"""State Orchestrator for the Campus Helpdesk Robot Workflow."""

import logging
from collections.abc import Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RobotStatus(Enum):
    """Robot operational states."""

    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()


class SessionController:
    """Manages robot conversation state machine and triggers STT, RAG, and TTS actions."""

    GREETING_TEXT = "Hello! Welcome to our campus. How may I assist you today?"

    def __init__(
        self,
        on_status_change: Callable[[RobotStatus], None] | None = None,
        on_message_received: Callable[[str, str], None] | None = None,  # (sender, text)
    ) -> None:
        self._status = RobotStatus.IDLE
        self._on_status_change = on_status_change
        self._on_message_received = on_message_received

    @property
    def status(self) -> RobotStatus:
        """Current status of the robot state machine."""
        return self._status

    def set_status(self, new_status: RobotStatus) -> None:
        """Update robot status and notify listener."""
        if self._status != new_status:
            logger.info(f"State transition: {self._status.name} -> {new_status.name}")
            self._status = new_status
            if self._on_status_change:
                self._on_status_change(new_status)

    def trigger_greeting(self) -> str:
        """Trigger single greeting when person is first detected."""
        if self._status == RobotStatus.IDLE:
            self.set_status(RobotStatus.SPEAKING)
            if self._on_message_received:
                self._on_message_received("Robot", self.GREETING_TEXT)
            return self.GREETING_TEXT
        return ""

    def user_left(self) -> None:
        """Reset state when person leaves camera view."""
        self.set_status(RobotStatus.IDLE)
