"""
src/campus_helpdesk/infrastructure/vision/tracker.py

Persistent Multi-Person Object Tracker for AUNTII Helpdesk Robot.
Assigns persistent IDs (e.g. ID #1, ID #2) to detected people across consecutive frames
using IoU matching and centroid distance estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TrackedPerson:
    """Represents a single tracked person across video frames."""

    track_id: int
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    centroid: Tuple[int, int]  # (cx, cy)
    confidence: float
    first_seen: float
    last_seen: float
    lost_count: int = 0
    is_active_user: bool = False

    @property
    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]


def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes (x, y, w, h)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]

    denom = float(boxAArea + boxBArea - interArea)
    if denom == 0:
        return 0.0
    return interArea / denom


class ByteTracker:
    """
    Persistent Multi-Person Tracker based on IoU and centroid distance matching.
    """

    def __init__(self, max_lost_frames: int = 15, iou_threshold: float = 0.3) -> None:
        self.max_lost_frames = max_lost_frames
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: Dict[int, TrackedPerson] = {}

    def update(self, detections: List[Tuple[Tuple[int, int, int, int], float]]) -> List[TrackedPerson]:
        """
        Update tracks with new detections [(bbox, confidence), ...].

        Returns:
            List of active TrackedPerson objects for the current frame.
        """
        now = time.time()

        # Increment lost count for existing tracks
        for t in self.tracks.values():
            t.lost_count += 1

        unmatched_detections = list(range(len(detections)))
        matched_tracks = set()

        if self.tracks and detections:
            track_ids = list(self.tracks.keys())
            iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)

            for i, tid in enumerate(track_ids):
                for j, (det_box, _) in enumerate(detections):
                    iou_matrix[i, j] = compute_iou(self.tracks[tid].bbox, det_box)

            # Match greedily highest IoU first
            while True:
                if iou_matrix.size == 0:
                    break
                max_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                max_iou = iou_matrix[max_idx]

                if max_iou < self.iou_threshold:
                    break

                t_idx, d_idx = max_idx
                tid = track_ids[t_idx]

                if tid not in matched_tracks and d_idx in unmatched_detections:
                    det_box, conf = detections[d_idx]
                    cx = det_box[0] + det_box[2] // 2
                    cy = det_box[1] + det_box[3] // 2

                    self.tracks[tid].bbox = det_box
                    self.tracks[tid].centroid = (cx, cy)
                    self.tracks[tid].confidence = conf
                    self.tracks[tid].last_seen = now
                    self.tracks[tid].lost_count = 0

                    matched_tracks.add(tid)
                    unmatched_detections.remove(d_idx)

                iou_matrix[t_idx, :] = -1
                iou_matrix[:, d_idx] = -1

        # Register new tracks for unmatched detections
        for d_idx in unmatched_detections:
            det_box, conf = detections[d_idx]
            cx = det_box[0] + det_box[2] // 2
            cy = det_box[1] + det_box[3] // 2

            new_track = TrackedPerson(
                track_id=self.next_id,
                bbox=det_box,
                centroid=(cx, cy),
                confidence=conf,
                first_seen=now,
                last_seen=now,
                lost_count=0,
            )
            self.tracks[self.next_id] = new_track
            self.next_id += 1

        # Remove stale tracks
        stale_ids = [tid for tid, t in self.tracks.items() if t.lost_count > self.max_lost_frames]
        for tid in stale_ids:
            del self.tracks[tid]

        return [t for t in self.tracks.values() if t.lost_count == 0]
