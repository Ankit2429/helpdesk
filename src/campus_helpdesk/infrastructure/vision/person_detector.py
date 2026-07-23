"""Offline OpenCV Person Detection with Hysteresis & Single Greeting logic."""

import logging
from typing import Callable, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PersonDetector:
    """Detects people in webcam feed and manages single-greeting hysteresis state."""

    def __init__(
        self,
        webcam_index: int = 0,
        reset_frames_threshold: int = 30,
        on_person_entered: Optional[Callable[[], None]] = None,
        on_person_left: Optional[Callable[[], None]] = None,
    ) -> None:
        self._webcam_index = webcam_index
        self._reset_frames_threshold = reset_frames_threshold
        self._on_person_entered = on_person_entered
        self._on_person_left = on_person_left

        self._person_present: bool = False
        self._missing_counter: int = 0
        self._cascade: Optional[cv2.CascadeClassifier] = None
        self._hog: Optional[cv2.HOGDescriptor] = None
        self._init_detector()

    def _init_detector(self) -> None:
        """Initialize OpenCV Haar cascades or HOG person detector."""
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Could not load Haar cascade classifier: {e}")

        # HOG descriptor fallback
        try:
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self._hog = hog
        except Exception as e:
            logger.warning(f"Could not load HOG people detector: {e}")

    @property
    def is_person_present(self) -> bool:
        """Return True if a person is currently detected in front of the camera."""
        return self._person_present

    def detect_in_frame(self, frame: np.ndarray) -> tuple[bool, np.ndarray]:
        """Process a single frame to detect person presence and annotate frame."""
        person_detected = False
        annotated_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Try Haar face detection
        if self._cascade is not None and not self._cascade.empty():
            faces = self._cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )
            if len(faces) > 0:
                person_detected = True
                for (x, y, w, h) in faces:
                    cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(
                        annotated_frame,
                        "Person Detected",
                        (x, max(0, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

        # 2. Fallback to HOG full body detection if face not detected
        if not person_detected and self._hog is not None:
            boxes, _ = self._hog.detectMultiScale(frame, winStride=(8, 8))
            if len(boxes) > 0:
                person_detected = True
                for (x, y, w, h) in boxes:
                    cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # State machine transition logic (Single Greeting Hysteresis)
        if person_detected:
            self._missing_counter = 0
            if not self._person_present:
                self._person_present = True
                logger.info("Person detected! Triggering greeting.")
                if self._on_person_entered:
                    self._on_person_entered()
        else:
            if self._person_present:
                self._missing_counter += 1
                if self._missing_counter >= self._reset_frames_threshold:
                    self._person_present = False
                    self._missing_counter = 0
                    logger.info("Person left camera frame. Resetting detector.")
                    if self._on_person_left:
                        self._on_person_left()

        return person_detected, annotated_frame

    def reset(self) -> None:
        """Reset detection state manually."""
        self._person_present = False
        self._missing_counter = 0
