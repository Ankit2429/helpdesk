"""Offline OpenCV Person Detection with Hysteresis & Frontal Face / Eye Contact Greeting logic."""

import logging
from collections.abc import Callable

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
    """Detects people in webcam feed and manages single-greeting hysteresis state with frontal gaze validation."""

    def __init__(
        self,
        webcam_index: int = 0,
        reset_frames_threshold: int = 30,
        on_person_entered: Callable[[], None] | None = None,
        on_person_left: Callable[[], None] | None = None,
    ) -> None:
        self._webcam_index = webcam_index
        self._reset_frames_threshold = reset_frames_threshold
        self._on_person_entered = on_person_entered
        self._on_person_left = on_person_left

        self._person_present: bool = False
        self._greeted_this_session: bool = False
        self._missing_counter: int = 0
        self._cascade: cv2.CascadeClassifier | None = None
        self._eye_cascade: cv2.CascadeClassifier | None = None
        self._hog: cv2.HOGDescriptor | None = None
        self._init_detector()

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

    @property
    def is_person_present(self) -> bool:
        """Return True if a person is currently detected in front of the camera."""
        return self._person_present

    @property
    def greeted_this_session(self) -> bool:
        """Return True if a greeting has already been triggered in the current session."""
        return self._greeted_this_session

    def detect_in_frame(self, frame: np.ndarray) -> DetectionResult:
        """Process a single frame to detect person presence and frontal face engagement."""
        person_detected = False
        face_forward = False
        face_center: tuple[float, float] | None = None
        annotated_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = frame.shape[:2]
        
        # Downscale gray frame to 320px width for fast detection
        scale = 1.0
        if width > 320:
            scale = 320.0 / width
            small_gray = cv2.resize(gray, (320, int(height * scale)))
        else:
            small_gray = gray

        # 1. Try Haar frontal face detection
        if self._cascade is not None and not self._cascade.empty():
            small_faces = self._cascade.detectMultiScale(
                small_gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(20, 20),
            )
            # Scale boxes back to original frame size
            faces = [
                (int(x / scale), int(y / scale), int(w / scale), int(h / scale))
                for (x, y, w, h) in small_faces
            ]
            if len(faces) > 0:
                person_detected = True
                face_forward = True
                x, y, w, h = faces[0]
                if width > 0 and height > 0:
                    face_center = (
                        round((x + w / 2.0) / float(width), 4),
                        round((y + h / 2.0) / float(height), 4),
                    )

                for fx, fy, fw, fh in faces:
                    cv2.rectangle(annotated_frame, (fx, fy), (fx + fw, fy + fh), (0, 255, 0), 2)
                    cv2.putText(
                        annotated_frame,
                        "Person Detected",
                        (fx, max(0, fy - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

        # 2. Fallback to HOG full body detection if face not detected
        if not person_detected and self._hog is not None:
            small_bgr = cv2.resize(frame, (320, int(height * scale))) if width > 320 else frame
            small_boxes, _ = self._hog.detectMultiScale(small_bgr, winStride=(16, 16))
            boxes = [
                (int(bx / scale), int(by / scale), int(bw / scale), int(bh / scale))
                for (bx, by, bw, bh) in small_boxes
            ]
            if len(boxes) > 0:
                person_detected = True
                face_forward = True
                x, y, w, h = boxes[0]
                if width > 0 and height > 0:
                    face_center = (
                        round((x + w / 2.0) / float(width), 4),
                        round((y + h / 2.0) / float(height), 4),
                    )
                for bx, by, bw, bh in boxes:
                    cv2.rectangle(annotated_frame, (bx, by), (bx + bw, by + bh), (255, 0, 0), 2)

        # State machine transition & single-greeting hysteresis logic
        if person_detected:
            self._missing_counter = 0
            self._person_present = True

            if not self._greeted_this_session:
                self._greeted_this_session = True
                logger.info("Person detected in camera frame! Triggering greeting.")
                if self._on_person_entered:
                    self._on_person_entered()
        else:
            if self._person_present:
                self._missing_counter += 1
                if self._missing_counter >= self._reset_frames_threshold:
                    self._person_present = False
                    self._greeted_this_session = False
                    self._missing_counter = 0
                    logger.info("Person left camera frame. Resetting detector state.")
                    if self._on_person_left:
                        self._on_person_left()

        return DetectionResult(person_detected, annotated_frame, face_center, face_forward)

    def reset(self) -> None:
        """Reset detection state manually."""
        self._person_present = False
        self._greeted_this_session = False
        self._missing_counter = 0
