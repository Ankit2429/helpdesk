"""Unit tests for PersonDetector state machine and debouncing."""

import numpy as np
import pytest
from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector


def test_person_detector_initial_state() -> None:
    detector = PersonDetector(reset_frames_threshold=5)
    assert not detector.is_person_present


def test_person_detector_hysteresis_reset() -> None:
    entered_calls = 0
    left_calls = 0

    def on_entered():
        nonlocal entered_calls
        entered_calls += 1

    def on_left():
        nonlocal left_calls
        left_calls += 1

    detector = PersonDetector(
        reset_frames_threshold=3,
        on_person_entered=on_entered,
        on_person_left=on_left,
    )

    # Force person present state directly for testing debounce
    detector._person_present = True

    # Empty frame (no person detected)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    # Frame 1 missing
    detector.detect_in_frame(frame)
    assert detector.is_person_present
    assert left_calls == 0

    # Frame 2 missing
    detector.detect_in_frame(frame)
    assert detector.is_person_present
    assert left_calls == 0

    # Frame 3 missing -> triggers reset
    detector.detect_in_frame(frame)
    assert not detector.is_person_present
    assert left_calls == 1
