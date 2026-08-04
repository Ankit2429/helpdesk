"""
src/campus_helpdesk/infrastructure/vision/intent_engine.py

Perception Engine & Intent State Machine for AUNTII Helpdesk Robot.
Replaces simple face-count greeting logic with intention detection:
1. Selects ONLY ONE primary candidate (closest / largest person in 1.0-1.5m interaction zone).
2. Ignores background passersby and onlookers.
3. Verifies continuous head pose & gaze engagement for >= 2.0 seconds before confirming attention.
4. Manages Perception State Machine: IDLE -> PERSON_DETECTED -> TRACKING -> ATTENTION_CONFIRMED -> INTERACTION.
5. Gracefully resets to IDLE if user turns away or leaves for > 1.0 second.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from campus_helpdesk.infrastructure.vision.gaze_estimator import GazeResult, HeadPoseGazeEstimator
from campus_helpdesk.infrastructure.vision.tracker import ByteTracker, TrackedPerson

logger = logging.getLogger("campus_helpdesk.intent_engine")


class RobotPerceptionState(Enum):
    IDLE = "IDLE"
    PERSON_DETECTED = "PERSON_DETECTED"
    TRACKING = "TRACKING"
    VERIFY_INTENT = "VERIFY_INTENT"
    ATTENTION_CONFIRMED = "ATTENTION_CONFIRMED"
    GREETING = "GREETING"
    INTERACTION = "INTERACTION"


@dataclass
class IntentResult:
    state: RobotPerceptionState
    active_person: Optional[TrackedPerson]
    gaze: Optional[GazeResult]
    annotated_frame: np.ndarray
    engagement_sec: float
    disengage_sec: float
    greeting_text: Optional[str] = None


class IntentPerceptionEngine:
    """
    Intention-based perception pipeline managing tracking, single-user selection, head pose/gaze,
    and robot state machine transitions.
    """

    def __init__(
        self,
        min_interaction_dist: float = 0.5,
        max_interaction_dist: float = 2.0,
        engagement_required_sec: float = 2.0,
        disengage_timeout_sec: float = 1.0,
        on_user_engaged: Optional[Callable[[TrackedPerson], None]] = None,
        on_user_disengaged: Optional[Callable[[], None]] = None,
        on_greeting_triggered: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.min_dist = min_interaction_dist
        self.max_dist = max_interaction_dist
        self.engagement_required_sec = engagement_required_sec
        self.disengage_timeout_sec = disengage_timeout_sec

        self.on_user_engaged = on_user_engaged
        self.on_user_disengaged = on_user_disengaged
        self.on_greeting_triggered = on_greeting_triggered
        self.active_language: str = "en"

        from campus_helpdesk.infrastructure.vision.greeting_manager import GreetingManager

        self.greeting_manager = GreetingManager(cooldown_seconds=7.0)
        self.tracker = ByteTracker(max_lost_frames=15, iou_threshold=0.3)
        self.gaze_estimator = HeadPoseGazeEstimator()

        self.state = RobotPerceptionState.IDLE
        self.active_track_id: Optional[int] = None
        self.engagement_start_time: Optional[float] = None
        self.disengage_start_time: Optional[float] = None

    def process_frame(
        self, frame: np.ndarray, raw_detections: List[Tuple[Tuple[int, int, int, int], float]]
    ) -> IntentResult:
        """
        Process single video frame with person detections [(bbox, conf), ...].
        """
        now = time.time()
        annotated_frame = frame.copy()
        h_img, w_img = frame.shape[:2]

        # 1. Update multi-person tracking
        tracked_persons = self.tracker.update(raw_detections)

        if not tracked_persons:
            if self.state != RobotPerceptionState.IDLE:
                self._check_disengagement_timeout(now)
            self._draw_state_overlay(annotated_frame, None, None, 0.0)
            return IntentResult(
                state=self.state,
                active_person=None,
                gaze=None,
                annotated_frame=annotated_frame,
                engagement_sec=0.0,
                disengage_sec=0.0,
            )

        # 2. Select SINGLE Primary Candidate in Interaction Zone
        # Filter candidate people whose distance is within interaction zone (0.5m - 2.0m)
        # Select largest bounding box area / closest candidate
        candidate_persons = []
        for p in tracked_persons:
            fx, fy, fw, fh = p.bbox
            # Fast distance estimate from box width
            est_dist = round(float((0.15 * w_img) / max(10, fw)), 2)
            if self.min_dist <= est_dist <= self.max_dist:
                candidate_persons.append((p, est_dist))

        # Sort candidates: closest distance (largest box) wins
        candidate_persons.sort(key=lambda x: (-x[0].area, x[1]))

        primary_person: Optional[TrackedPerson] = None
        primary_dist: float = 0.0

        if candidate_persons:
            primary_person, primary_dist = candidate_persons[0]

        # 3. Handle Active User Selection & Lock-on
        if self.active_track_id is not None:
            # Check if active person is still present in current tracks
            active_matches = [p for p in tracked_persons if p.track_id == self.active_track_id]
            if active_matches:
                primary_person = active_matches[0]
                fx, fy, fw, fh = primary_person.bbox
                primary_dist = round(float((0.15 * w_img) / max(10, fw)), 2)
            else:
                # Active user lost
                primary_person = None

        # State transition: IDLE -> PERSON_DETECTED -> TRACKING -> VERIFY_INTENT
        if self.state == RobotPerceptionState.IDLE and tracked_persons:
            self.state = RobotPerceptionState.PERSON_DETECTED

        if self.state in (RobotPerceptionState.PERSON_DETECTED, RobotPerceptionState.IDLE) and primary_person:
            self.state = RobotPerceptionState.TRACKING
            self.active_track_id = primary_person.track_id

        # 4. Head Pose & Eye Gaze Estimation for Primary User
        active_gaze: Optional[GazeResult] = None
        is_engaged_now = False

        if primary_person is not None:
            active_gaze = self.gaze_estimator.estimate(frame, primary_person.bbox)

            # Engagement Rule: Within distance + Pitch/Yaw <= 20° + Looking
            if (
                self.min_dist <= active_gaze.distance_m <= self.max_dist
                and active_gaze.is_looking
            ):
                is_engaged_now = True

        if self.state == RobotPerceptionState.TRACKING and is_engaged_now:
            self.state = RobotPerceptionState.VERIFY_INTENT

        # 5. Temporal Intent State Machine Logic
        engagement_sec = 0.0
        disengage_sec = 0.0
        generated_greeting: Optional[str] = None

        if is_engaged_now and primary_person is not None:
            self.disengage_start_time = None
            if self.engagement_start_time is None:
                self.engagement_start_time = now

            engagement_sec = round(now - self.engagement_start_time, 1)

            # Confirm attention after continuous 2.0 seconds
            if (
                self.state in (RobotPerceptionState.VERIFY_INTENT, RobotPerceptionState.TRACKING, RobotPerceptionState.PERSON_DETECTED)
                and engagement_sec >= self.engagement_required_sec
            ):
                self.state = RobotPerceptionState.ATTENTION_CONFIRMED
                logger.info(
                    f"[Intent Confirmed] Active User (ID #{primary_person.track_id}) "
                    f"engaged continuously for {engagement_sec:.1f}s."
                )

                if hasattr(self, "greeting_manager") and not self.greeting_manager.is_cooldown_active(primary_person.track_id):
                    self.state = RobotPerceptionState.GREETING
                    generated_greeting = self.greeting_manager.generate_greeting(
                        user_id=primary_person.track_id,
                        language=self.active_language,
                    )
                    logger.info(f"[Greeting Event Fired] Text='{generated_greeting}' (Language='{self.active_language}')")
                    if hasattr(self, "on_greeting_triggered") and self.on_greeting_triggered:
                        try:
                            self.on_greeting_triggered(generated_greeting, self.active_language)
                        except Exception as cb_err:
                            logger.warning(f"Error in on_greeting_triggered callback: {cb_err}")

                self.state = RobotPerceptionState.INTERACTION
                if self.on_user_engaged:
                    self.on_user_engaged(primary_person)

        else:
            # User is NOT engaged (looking away or moved out of zone)
            self.engagement_start_time = None
            if self.state in (RobotPerceptionState.VERIFY_INTENT, RobotPerceptionState.ATTENTION_CONFIRMED, RobotPerceptionState.GREETING, RobotPerceptionState.INTERACTION):
                if self.disengage_start_time is None:
                    self.disengage_start_time = now
                disengage_sec = round(now - self.disengage_start_time, 1)

                if disengage_sec >= self.disengage_timeout_sec:
                    logger.info(
                        f"[User Disengaged] Active User turned away for {disengage_sec:.1f}s. "
                        f"Resetting perception state machine to IDLE."
                    )
                    self.state = RobotPerceptionState.IDLE
                    self.active_track_id = None
                    self.disengage_start_time = None
                    if self.on_user_disengaged:
                        self.on_user_disengaged()
            elif self.state in (RobotPerceptionState.TRACKING, RobotPerceptionState.PERSON_DETECTED):
                self.state = RobotPerceptionState.IDLE
                self.active_track_id = None

        # 6. Render Visual Diagnostic Overlays
        self._draw_diagnostic_overlays(
            annotated_frame, tracked_persons, primary_person, active_gaze
        )
        self._draw_state_overlay(
            annotated_frame, primary_person, active_gaze, engagement_sec if is_engaged_now else disengage_sec
        )

        return IntentResult(
            state=self.state,
            active_person=primary_person,
            gaze=active_gaze,
            annotated_frame=annotated_frame,
            engagement_sec=engagement_sec,
            disengage_sec=disengage_sec,
        )

    def _check_disengagement_timeout(self, now: float) -> None:
        """Handle timeout reset when active user leaves frame."""
        if self.disengage_start_time is None:
            self.disengage_start_time = now

        if now - self.disengage_start_time >= self.disengage_timeout_sec:
            logger.info("Active user left frame. Resetting state machine to IDLE.")
            self.state = RobotPerceptionState.IDLE
            self.active_track_id = None
            self.disengage_start_time = None
            if self.on_user_disengaged:
                self.on_user_disengaged()

    def _draw_diagnostic_overlays(
        self,
        frame: np.ndarray,
        all_persons: List[TrackedPerson],
        active_person: Optional[TrackedPerson],
        active_gaze: Optional[GazeResult],
    ) -> None:
        """Render diagnostic bounding boxes, Track IDs, head pose angles, and gaze status."""
        for p in all_persons:
            x, y, w, h = p.bbox
            is_active = active_person is not None and p.track_id == active_person.track_id

            color = (0, 255, 0) if is_active else (150, 150, 150)  # Green for active, Gray for ignored
            thickness = 3 if is_active else 1

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)

            # Label box header
            status_text = f"ID #{p.track_id} {'[ACTIVE USER]' if is_active else '[IGNORED]'}"
            cv2.rectangle(frame, (x, max(0, y - 24)), (x + w, y), color, -1)
            cv2.putText(
                frame,
                status_text,
                (x + 4, max(14, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0) if is_active else (255, 255, 255),
                2,
            )

            # Active user metrics detail overlay
            if is_active and active_gaze:
                metrics_str = (
                    f"Dist: {active_gaze.distance_m:.1f}m | "
                    f"Pose: P:{active_gaze.pitch:+.1f}° Y:{active_gaze.yaw:+.1f}° | "
                    f"{active_gaze.gaze_label}"
                )
                cv2.putText(
                    frame,
                    metrics_str,
                    (x, y + h + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    2,
                )

    def _draw_state_overlay(
        self,
        frame: np.ndarray,
        active_person: Optional[TrackedPerson],
        gaze: Optional[GazeResult],
        timer_sec: float,
    ) -> None:
        """Render main perception state badge on top left of frame."""
        state_str = f"ROBOT PERCEPTION STATE: [{self.state.value}]"
        badge_color = (0, 200, 255)  # Amber

        if self.state == RobotPerceptionState.INTERACTION:
            badge_color = (0, 255, 0)  # Green
        elif self.state == RobotPerceptionState.IDLE:
            badge_color = (120, 120, 120)  # Gray

        cv2.rectangle(frame, (10, 10), (520, 48), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (520, 48), badge_color, 2)
        cv2.putText(
            frame,
            state_str,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            badge_color,
            2,
        )

        if active_person and gaze:
            timer_text = f"Continuous Engagement: {timer_sec:.1f}s / {self.engagement_required_sec:.1f}s"
            cv2.putText(
                frame,
                timer_text,
                (20, 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

    def reset(self) -> None:
        """Reset perception state machine manually."""
        self.state = RobotPerceptionState.IDLE
        self.active_track_id = None
        self.engagement_start_time = None
        self.disengage_start_time = None
