"""
presence_service.py
Offline camera-based presence detection using OpenCV's built-in Haar cascade
face detector (ships with opencv-python, no model download needed).

Behavior:
- Watches the camera in a background thread, checking for a face every
  CHECK_INTERVAL seconds (not every frame -- keeps CPU usage low on Pi).
- When a face first appears -> fires on_person_arrived() ONCE (this is
  where you trigger the welcome greeting).
- While a face keeps being seen, stays "present" silently (no repeat greetings).
- If no face is seen for ABSENCE_TIMEOUT seconds -> resets to "away", so the
  next arrival greets again.
- After greeting, the assistant should switch to wake-word-only listening
  (see assistant_loop.py) -- this module ONLY handles presence, not commands.

Install:
    pip install opencv-python
"""

import os
import sys
import time
import logging
import threading

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("presence_service")

# ---- Config ------------------------------------------------------------------
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CHECK_INTERVAL = float(os.getenv("PRESENCE_CHECK_INTERVAL", "1.0"))   # seconds between checks
ABSENCE_TIMEOUT = float(os.getenv("PRESENCE_ABSENCE_TIMEOUT", "20"))  # seconds with no face -> "away"
DETECT_SCALE = 0.5  # downscale frame before detection, big speedup on Pi CPU


class PresenceService:
    """
    Runs face detection on a background thread and calls callbacks on
    arrival / departure. Does not block the rest of the assistant.
    """

    def __init__(self, on_person_arrived=None, on_person_left=None):
        self.on_person_arrived = on_person_arrived or (lambda: None)
        self.on_person_left = on_person_left or (lambda: None)

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        if self.detector.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {cascade_path}")

        self._present = False
        self._last_seen = 0.0
        self._running = False
        self._thread = None

    def _face_visible(self, frame) -> bool:
        small = cv2.resize(frame, None, fx=DETECT_SCALE, fy=DETECT_SCALE)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(30, 30)
        )
        return len(faces) > 0

    def _watch_loop(self):
        backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_DSHOW
        cap = cv2.VideoCapture(CAMERA_INDEX, backend)
        if not cap.isOpened():
            cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            logger.error(f"Could not open camera index {CAMERA_INDEX}")
            return

        logger.info("Presence watcher started.")
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(CHECK_INTERVAL)
                    continue

                if self._face_visible(frame):
                    self._last_seen = time.time()
                    if not self._present:
                        self._present = True
                        logger.info("Person arrived.")
                        self.on_person_arrived()
                else:
                    if self._present and (time.time() - self._last_seen) > ABSENCE_TIMEOUT:
                        self._present = False
                        logger.info("Person left (no face for %.0fs).", ABSENCE_TIMEOUT)
                        self.on_person_left()

                time.sleep(CHECK_INTERVAL)
        finally:
            cap.release()
            logger.info("Presence watcher stopped.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def is_present(self) -> bool:
        return self._present


# ---- Quick manual test --------------------------------------------------------
if __name__ == "__main__":
    def greet():
        print(">>> WELCOME! (this is where TTS would say hello)")

    def bye():
        print(">>> Person left, resetting.")

    service = PresenceService(on_person_arrived=greet, on_person_left=bye)
    service.start()

    print("Watching camera. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
