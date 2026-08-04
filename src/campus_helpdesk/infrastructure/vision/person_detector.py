"""Offline OpenCV Person Detection with Hysteresis & Frontal Face / Eye Contact Greeting logic."""

import logging
from collections.abc import Callable
from typing import Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class DetectionResult(tuple):
    """Result object returned by detect_in_frame preserving 2-tuple unpacking compatibility."""

    person_detected: bool
    annotated_frame: np.ndarray
    face_center: tuple[float, float] | None
    face_forward: bool

    def __new__(
        cls,
        person_detected: bool,
        annotated_frame: np.ndarray,
        face_center: tuple[float, float] | None = None,
        face_forward: bool = False,
    ):
        return super().__new__(cls, (person_detected, annotated_frame))

    def __init__(
        self,
        person_detected: bool,
        annotated_frame: np.ndarray,
        face_center: tuple[float, float] | None = None,
        face_forward: bool = False,
    ) -> None:
        self.person_detected = person_detected
        self.annotated_frame = annotated_frame
        self.face_center = face_center
        self.face_forward = face_forward


class PersonDetector:
    """Detects people in webcam feed and manages intent-based single user engagement and gaze validation."""

    def __init__(
        self,
        webcam_index: int = 0,
        reset_frames_threshold: int = 30,
        on_person_entered: Callable[[], None] | None = None,
        on_person_left: Callable[[], None] | None = None,
        on_greeting_triggered: Callable[[str, str], None] | None = None,
    ) -> None:
        self._webcam_index = webcam_index
        self._reset_frames_threshold = reset_frames_threshold
        self._on_person_entered = on_person_entered
        self._on_person_left = on_person_left
        self._on_greeting_triggered = on_greeting_triggered

        self._person_present: bool = False
        self._greeted_this_session: bool = False
        self._missing_counter: int = 0
        self._cascade: cv2.CascadeClassifier | None = None
        self._eye_cascade: cv2.CascadeClassifier | None = None
        self._hog: cv2.HOGDescriptor | None = None
        self._init_detector()

        from campus_helpdesk.infrastructure.vision.intent_engine import IntentPerceptionEngine

        self.intent_engine = IntentPerceptionEngine(
            min_interaction_dist=0.5,
            max_interaction_dist=2.0,
            engagement_required_sec=2.0,
            disengage_timeout_sec=1.0,
            on_user_engaged=self._handle_user_engaged,
            on_user_disengaged=self._handle_user_disengaged,
            on_greeting_triggered=self._handle_greeting_triggered,
        )

    def _handle_greeting_triggered(self, greeting_text: str, language: str) -> None:
        """Callback fired when intent engine triggers a greeting."""
        logger.info(f"[Detector Greeting Triggered] Text='{greeting_text}' Language='{language}'")
        if self._on_greeting_triggered:
            self._on_greeting_triggered(greeting_text, language)

    def _init_detector(self) -> None:
        """Initialize OpenCV Haar cascades or HOG person detector."""
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Could not load Haar face cascade classifier: {e}")

        try:
            eye_cascade_path = cv2.data.haarcascades + "haarcascade_eye.xml"
            self._eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        except Exception as e:
            logger.warning(f"Could not load Haar eye cascade classifier: {e}")

        # HOG descriptor fallback for general body tracking
        try:
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self._hog = hog
        except Exception as e:
            logger.warning(f"Could not load HOG people detector: {e}")

    def _handle_user_engaged(self, active_user: Any) -> None:
        """Callback fired when a single user is confirmed engaged after 2s continuous attention."""
        if not self._greeted_this_session:
            self._greeted_this_session = True
            self._person_present = True
            logger.info(f"Active User (ID #{active_user.track_id}) confirmed engaged! Triggering greeting.")
            if self._on_person_entered:
                self._on_person_entered()

    def _handle_user_disengaged(self) -> None:
        """Callback fired when active user disengages or turns away for >1s."""
        if self._person_present:
            self._person_present = False
            self._greeted_this_session = False
            logger.info("Active User disengaged. Resetting session state.")
            if self._on_person_left:
                self._on_person_left()

    @property
    def is_person_present(self) -> bool:
        """Return True if an engaged active user is currently present."""
        return self._person_present

    @property
    def greeted_this_session(self) -> bool:
        """Return True if a greeting has been triggered for the active user."""
        return self._greeted_this_session

    def detect_in_frame(self, frame: np.ndarray) -> DetectionResult:
        """Process frame through intent perception engine with tracking, gaze, and state machine."""
        raw_detections = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = frame.shape[:2]

        # Downscale gray frame to 320px width for ultra-fast face/person detection
        scale = 1.0
        if width > 320:
            scale = 320.0 / width
            small_gray = cv2.resize(gray, (320, int(height * scale)))
        else:
            small_gray = gray

        # 1. Haar frontal face detection
        if self._cascade is not None and not self._cascade.empty():
            small_faces = self._cascade.detectMultiScale(
                small_gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(20, 20),
            )
            for (x, y, w, h) in small_faces:
                box = (int(x / scale), int(y / scale), int(w / scale), int(h / scale))
                raw_detections.append((box, 0.95))

        # 2. HOG person detector fallback if no faces detected
        if not raw_detections and self._hog is not None:
            small_bgr = cv2.resize(frame, (320, int(height * scale))) if width > 320 else frame
            small_boxes, _ = self._hog.detectMultiScale(small_bgr, winStride=(16, 16))
            for (bx, by, bw, bh) in small_boxes:
                box = (int(bx / scale), int(by / scale), int(bw / scale), int(bh / scale))
                raw_detections.append((box, 0.75))

        # 3. Process detections through Intention Perception Engine
        intent_res = self.intent_engine.process_frame(frame, raw_detections)

        person_detected = bool(raw_detections or intent_res.active_person)
        face_center = None
        if raw_detections:
            (x, y, w, h), _ = raw_detections[0]
            cx, cy = x + w / 2.0, y + h / 2.0
            face_center = (round(cx / float(width), 4), round(cy / float(height), 4))
        elif intent_res.active_person:
            cx, cy = intent_res.active_person.centroid
            face_center = (round(cx / float(width), 4), round(cy / float(height), 4))

        face_forward = intent_res.gaze.is_looking if intent_res.gaze else (len(raw_detections) > 0)

        if person_detected:
            self._missing_counter = 0
            if not self._greeted_this_session:
                self._greeted_this_session = True
                self._person_present = True
                if self._on_person_entered:
                    self._on_person_entered()
        else:
            self._missing_counter += 1
            if self._missing_counter >= self._reset_frames_threshold:
                if self._person_present:
                    self._person_present = False
                    self._greeted_this_session = False
                    if self._on_person_left:
                        self._on_person_left()

        return DetectionResult(
            person_detected=person_detected,
            annotated_frame=intent_res.annotated_frame,
            face_center=face_center,
            face_forward=face_forward,
        )

    def reset(self) -> None:
        """Reset detection and intent state manually."""
        self._person_present = False
        self._greeted_this_session = False
        self._missing_counter = 0
        if hasattr(self, "intent_engine"):
            self.intent_engine.reset()
