"""Unit tests for PersonDetector state machine and debouncing."""

import numpy as np

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


class DummyCascade:
    def __init__(self, faces):
        self._faces = faces

    def empty(self):
        return False

    def detectMultiScale(self, image, **kwargs):
        return np.array(self._faces)


def test_face_center_position_calculation() -> None:
    detector = PersonDetector()
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    # 1. No face detected -> face_center is None
    detector._cascade = DummyCascade([])
    res_empty = detector.detect_in_frame(frame)
    assert not res_empty.person_detected
    assert res_empty.face_center is None
    # Verify 2-tuple unpacking backward compatibility
    is_present, annotated = res_empty
    assert not is_present

    # 2. Face in center of 200x200 frame: bbox at (50, 50, 100, 100) -> center (100, 100) -> normalized (0.5, 0.5)
    detector._cascade = DummyCascade([(50, 50, 100, 100)])
    res_center = detector.detect_in_frame(frame)
    assert res_center.person_detected
    assert res_center.face_center == (0.5, 0.5)

    # 3. Face in top-left corner of 200x200 frame: bbox at (0, 0, 40, 40) -> center (20, 20) -> normalized (0.1, 0.1)
    detector._cascade = DummyCascade([(0, 0, 40, 40)])
    res_corner = detector.detect_in_frame(frame)
    assert res_corner.person_detected
    assert res_corner.face_center == (0.1, 0.1)

