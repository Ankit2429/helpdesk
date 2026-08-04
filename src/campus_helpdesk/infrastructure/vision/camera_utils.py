"""
src/campus_helpdesk/infrastructure/vision/camera_utils.py

Production-Grade Camera Utilities for AUNTII Helpdesk Robot.
Provides intelligent camera initialization, multi-index auto-discovery, DirectShow Windows backend support,
frame buffer optimization, and comprehensive diagnostics.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2

logger = logging.getLogger("campus_helpdesk.camera_utils")


def get_opencv_info() -> Dict[str, Any]:
    """Return OpenCV version and system platform metadata."""
    return {
        "opencv_version": cv2.__version__,
        "platform": sys.platform,
        "os_name": os.name,
        "is_windows": sys.platform == "win32" or os.name == "nt",
    }


def scan_available_cameras(max_indices: int = 4) -> List[Dict[str, Any]]:
    """
    Probe system video devices across camera indices (0..max_indices-1).

    Returns:
        List of dictionaries with metadata for working cameras.
    """
    info = get_opencv_info()
    is_win = info["is_windows"]
    available_cameras = []

    logger.info(f"Scanning camera indices 0..{max_indices - 1} (OS: {sys.platform}, OpenCV: {cv2.__version__})...")

    backends = [("DirectShow", cv2.CAP_DSHOW), ("CAP_ANY", cv2.CAP_ANY)] if is_win else [("CAP_ANY", cv2.CAP_ANY)]

    for idx in range(max_indices):
        for backend_name, backend_id in backends:
            try:
                cap = cv2.VideoCapture(idx, backend_id)
                if cap is not None and cap.isOpened():
                    # Test frame read
                    ret = False
                    frame = None
                    for _ in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            break
                        time.sleep(0.05)

                    if ret and frame is not None:
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)

                        cam_data = {
                            "index": idx,
                            "backend_name": backend_name,
                            "backend_id": backend_id,
                            "width": w,
                            "height": h,
                            "fps": fps,
                            "frame_shape": frame.shape,
                        }
                        logger.info(
                            f"[Camera Discovered] Index {idx} via {backend_name}: "
                            f"Resolution={w}x{h}, FPS={fps:.1f}"
                        )
                        available_cameras.append(cam_data)
                        cap.release()
                        break  # Found working backend for this index
                    cap.release()
            except Exception as err:
                logger.debug(f"Scan exception on index {idx} ({backend_name}): {err}")

    return available_cameras


def open_camera_intelligently(
    requested_index: int = 0,
    resolution: Tuple[int, int] = (1280, 720),
    target_fps: int = 30,
    fallback_indices: Optional[List[int]] = None,
) -> Tuple[Optional[cv2.VideoCapture], Dict[str, Any]]:
    """
    Intelligently open a hardware camera device with DirectShow on Windows,
    buffer size optimization, multi-index fallback, and diagnostics.

    Args:
        requested_index: Primary camera index to attempt.
        resolution: Preferred (width, height).
        target_fps: Preferred target FPS.
        fallback_indices: List of alternative camera indices to try if requested fails.

    Returns:
        Tuple of (VideoCapture instance or None, metadata_dict)
    """
    if fallback_indices is None:
        fallback_indices = [0, 1, 2]

    # Order candidate indices putting requested_index first
    if requested_index >= 90 or requested_index < 0:
        candidate_indices = [requested_index]
    else:
        candidate_indices = [requested_index] + [i for i in fallback_indices if i != requested_index]

    info = get_opencv_info()
    is_win = info["is_windows"]

    backends = [("DirectShow", cv2.CAP_DSHOW), ("CAP_ANY", cv2.CAP_ANY)] if is_win else [("CAP_ANY", cv2.CAP_ANY)]

    for idx in candidate_indices:
        for backend_name, backend_id in backends:
            logger.info(f"Attempting camera initialization: Index={idx}, Backend={backend_name}...")
            start_t = time.perf_counter()

            try:
                cap = cv2.VideoCapture(idx, backend_id)
                if cap is None or not cap.isOpened():
                    logger.warning(f"Failed opening camera index {idx} via {backend_name}.")
                    if cap:
                        cap.release()
                    continue

                # Configure requested resolution and FPS
                w_req, h_req = resolution
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w_req)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h_req)
                cap.set(cv2.CAP_PROP_FPS, target_fps)

                # Minimize internal buffer size to eliminate latency buildup
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                # Test frame capture with retry loop
                ret = False
                frame = None
                for attempt in range(1, 4):
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        break
                    logger.debug(f"Initial read retry {attempt}/3 on index {idx}...")
                    time.sleep(0.1)

                if ret and frame is not None:
                    act_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    act_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    act_fps = cap.get(cv2.CAP_PROP_FPS)
                    startup_ms = (time.perf_counter() - start_t) * 1000

                    meta = {
                        "status": "success",
                        "index": idx,
                        "backend_name": backend_name,
                        "backend_id": backend_id,
                        "width": act_w,
                        "height": act_h,
                        "fps": act_fps if act_fps > 0 else target_fps,
                        "startup_ms": round(startup_ms, 2),
                        "opencv_version": cv2.__version__,
                    }

                    logger.info(
                        f"[Camera Connected Successfully] Index={idx}, Backend={backend_name}, "
                        f"Resolution={act_w}x{act_h}, Startup={startup_ms:.1f}ms"
                    )
                    return cap, meta

                logger.warning(f"Camera opened on index {idx} via {backend_name}, but frame read failed.")
                cap.release()

            except Exception as exc:
                logger.error(f"Camera init exception on index {idx} ({backend_name}): {exc}")

    error_meta = {
        "status": "failed",
        "index": requested_index,
        "error": "No working camera device found across candidate indices.",
        "opencv_version": cv2.__version__,
    }
    logger.error("All camera initialization candidates failed.")
    return None, error_meta
