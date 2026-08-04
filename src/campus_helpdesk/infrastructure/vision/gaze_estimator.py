"""
src/campus_helpdesk/infrastructure/vision/gaze_estimator.py

Head Pose & Eye Gaze Estimation Module for AUNTII Helpdesk Robot.
Estimates 3D Head Pose (Pitch, Yaw, Roll), distance in meters, and eye gaze direction
(Looking vs Not Looking) using MediaPipe Face Mesh with OpenCV solvePnP fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger("campus_helpdesk.gaze_estimator")


@dataclass
class GazeResult:
    """Structure storing head pose and gaze metrics for a detected face."""

    pitch: float  # Up / Down angle in degrees
    yaw: float  # Left / Right angle in degrees
    roll: float  # Tilt angle in degrees
    distance_m: float  # Estimated distance in meters
    is_looking: bool  # True if pitch & yaw within ±20° facing camera
    gaze_label: str  # "👁️ Looking" or "🙈 Not Looking"


class HeadPoseGazeEstimator:
    """
    Estimates 3D head pose orientation and eye gaze direction.
    """

    def __init__(self) -> None:
        self._mp_face_mesh = None
        self._mesh = None
        self._init_mediapipe()

        # 3D generic facial model points (Nose tip, Chin, Left eye corner, Right eye corner, Left mouth, Right mouth)
        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),  # Nose tip
                (0.0, -330.0, -65.0),  # Chin
                (-225.0, 170.0, -135.0),  # Left eye left corner
                (225.0, 170.0, -135.0),  # Right eye right corner
                (-150.0, -150.0, -125.0),  # Left Mouth corner
                (150.0, -150.0, -125.0),  # Right mouth corner
            ],
            dtype=np.float64,
        )

    def _init_mediapipe(self) -> None:
        """Initialize MediaPipe Face Mesh if installed."""
        try:
            import mediapipe as mp

            self._mp_face_mesh = mp.solutions.face_mesh
            self._mesh = self._mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            logger.info("MediaPipe Face Mesh initialized for head pose & gaze estimation.")
        except Exception as err:
            logger.warning(f"MediaPipe Face Mesh unavailable ({err}); using OpenCV solvePnP fallback.")
            self._mesh = None

    def estimate(
        self, frame: np.ndarray, face_box: tuple[int, int, int, int]
    ) -> GazeResult:
        """
        Estimate head pose, distance, and gaze for face region (x, y, w, h).
        """
        h_img, w_img = frame.shape[:2]
        fx, fy, fw, fh = face_box

        # Estimate distance in meters (approximate focal length calibration: f ~ 800)
        # Real average human face width is ~0.15m
        focal_length = w_img
        distance_m = round(float((0.15 * focal_length) / max(10, fw)), 2)

        # 1. Try MediaPipe Face Mesh if available
        if self._mesh is not None:
            try:
                # Crop face ROI with padding for high-precision mesh
                pad = int(0.2 * max(fw, fh))
                x1 = max(0, fx - pad)
                y1 = max(0, fy - pad)
                x2 = min(w_img, fx + fw + pad)
                y2 = min(h_img, fy + fh + pad)

                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                    results = self._mesh.process(rgb_roi)

                    if results.multi_face_landmarks:
                        landmarks = results.multi_face_landmarks[0].landmark
                        roi_h, roi_w = roi.shape[:2]

                        # Extract key landmark points (Nose: 1, Chin: 152, L Eye: 33, R Eye: 263, L Mouth: 61, R Mouth: 291)
                        image_points = np.array(
                            [
                                (landmarks[1].x * roi_w, landmarks[1].y * roi_h),
                                (landmarks[152].x * roi_w, landmarks[152].y * roi_h),
                                (landmarks[33].x * roi_w, landmarks[33].y * roi_h),
                                (landmarks[263].x * roi_w, landmarks[263].y * roi_h),
                                (landmarks[61].x * roi_w, landmarks[61].y * roi_h),
                                (landmarks[291].x * roi_w, landmarks[291].y * roi_h),
                            ],
                            dtype=np.float64,
                        )

                        # Camera matrix approximation
                        center = (roi_w / 2.0, roi_h / 2.0)
                        camera_matrix = np.array(
                            [[roi_w, 0, center[0]], [0, roi_w, center[1]], [0, 0, 1]],
                            dtype=np.float64,
                        )
                        dist_coeffs = np.zeros((4, 1))

                        success, rotation_vec, translation_vec = cv2.solvePnP(
                            self.model_points,
                            image_points,
                            camera_matrix,
                            dist_coeffs,
                            flags=cv2.SOLVEPNP_ITERATIVE,
                        )

                        if success:
                            rmat, _ = cv2.Rodrigues(rotation_vec)
                            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

                            pitch = float(angles[0])
                            yaw = float(angles[1])
                            roll = float(angles[2])

                            # User is looking if pitch and yaw are facing camera (<= ±20 degrees)
                            is_looking = abs(pitch) <= 20.0 and abs(yaw) <= 20.0
                            label = "👁️ Looking" if is_looking else "🙈 Not Looking"

                            return GazeResult(
                                pitch=round(pitch, 1),
                                yaw=round(yaw, 1),
                                roll=round(roll, 1),
                                distance_m=distance_m,
                                is_looking=is_looking,
                                gaze_label=label,
                            )
            except Exception as mp_err:
                logger.debug(f"MediaPipe estimation error: {mp_err}")

        # 2. OpenCV Fallback: Geometry-based gaze approximation from face box position
        # Centering check: Face box near center of FOV
        center_x = fx + fw / 2.0
        center_y = fy + fh / 2.0

        yaw_approx = round(float((center_x - (w_img / 2.0)) / (w_img / 2.0) * 30.0), 1)
        pitch_approx = round(float((center_y - (h_img / 2.0)) / (h_img / 2.0) * 20.0), 1)

        is_looking = abs(yaw_approx) <= 20.0 and abs(pitch_approx) <= 20.0
        label = "👁️ Looking" if is_looking else "🙈 Not Looking"

        return GazeResult(
            pitch=pitch_approx,
            yaw=yaw_approx,
            roll=0.0,
            distance_m=distance_m,
            is_looking=is_looking,
            gaze_label=label,
        )
