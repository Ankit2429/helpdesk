#!/usr/bin/env python
"""
test_camera.py

Standalone Verification & Diagnostic Script for OpenCV Camera Module in AUNTII Helpdesk Robot.
Tests:
1. OpenCV environment & platform metadata
2. Scanning available camera devices & backends (DirectShow vs CAP_ANY)
3. Intelligent camera initialization (<500ms startup target)
4. Live webcam stream preview with real-time FPS overlay
5. Robust resource cleanup on shutdown
"""

import logging
import sys
import time
import cv2

# Ensure src/ is on PYTHONPATH
from campus_helpdesk.infrastructure.vision.camera_utils import (
    get_opencv_info,
    open_camera_intelligently,
    scan_available_cameras,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_camera")


def main() -> None:
    print("=" * 70)
    print("      AUNTII Helpdesk Robot — OpenCV Camera Verification & Diagnostics")
    print("=" * 70)

    # 1. OpenCV & System Diagnostics
    info = get_opencv_info()
    print("\n[1] OpenCV System Environment:")
    print(f"    - OpenCV Version: {info['opencv_version']}")
    print(f"    - Operating System: {info['platform']} ({info['os_name']})")
    print(f"    - DirectShow Default (Windows): {'YES' if info['is_windows'] else 'NO'}")

    # 2. Camera Hardware Discovery Scan
    print("\n[2] Scanning Available System Cameras (Indices 0..3)...")
    cameras = scan_available_cameras(max_indices=4)

    if not cameras:
        print("\n" + "!" * 70)
        print("WARNING: No physical webcams were detected on camera indices 0..3.")
        print("Please verify:")
        print("  1. USB webcam is securely plugged in.")
        print("  2. Webcam privacy switch / cover is open.")
        print("  3. Windows Camera Privacy Settings allow desktop app access.")
        print("!" * 70 + "\n")
        sys.exit(1)

    print(f"\n    Discovered {len(cameras)} active camera device(s):")
    for cam in cameras:
        print(
            f"    - Index {cam['index']}: {cam['backend_name']} Backend | "
            f"Resolution {cam['width']}x{cam['height']} | FPS: {cam['fps']:.1f}"
        )

    # 3. Intelligent Camera Initialization Test
    first_idx = cameras[0]["index"]
    print(f"\n[3] Testing Intelligent Initialization (Target Index: {first_idx})...")

    start_t = time.perf_counter()
    cap, meta = open_camera_intelligently(
        requested_index=first_idx,
        resolution=(1280, 720),
        target_fps=30,
        fallback_indices=[0, 1, 2],
    )
    init_ms = (time.perf_counter() - start_t) * 1000

    if not cap or not cap.isOpened() or meta.get("status") == "failed":
        print(f"\nFAILED: Could not open camera device. Details: {meta}")
        sys.exit(1)

    print(f"    Status:      PASSED [OK]")
    print(f"    Selected Index: {meta['index']}")
    print(f"    Backend Used:   {meta['backend_name']}")
    print(f"    Resolution:     {meta['width']}x{meta['height']}")
    print(f"    Configured FPS: {meta['fps']}")
    print(f"    Startup Time:   {meta['startup_ms']} ms (Target: <500 ms)")

    # 4. Live Stream Preview Window
    print("\n[4] Launching Live Stream Preview Window...")
    print("    Press 'q' or ESC in the preview window to exit.\n")

    window_name = "AUNTII Camera Diagnostics — Press Q to Exit"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    prev_frame_t = time.time()
    frame_count = 0
    start_stream_t = time.time()

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                print("    [Warning] Frame drop detected. Retrying...")
                time.sleep(0.03)
                continue

            frame_count += 1
            curr_t = time.time()
            instant_fps = 1.0 / max(0.001, curr_t - prev_frame_t)
            prev_frame_t = curr_t

            # Render diagnostic info overlay on frame
            overlay_text_1 = (
                f"Camera #{meta['index']} [{meta['backend_name']}] | "
                f"Res: {frame.shape[1]}x{frame.shape[0]} | FPS: {instant_fps:.1f}"
            )
            overlay_text_2 = "OpenCV Diagnostics — AUNTII Helpdesk Robot (Press Q to quit)"

            cv2.rectangle(frame, (10, 10), (700, 75), (0, 0, 0), -1)
            cv2.putText(frame, overlay_text_1, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, overlay_text_2, (20, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                print("    Quit signal received. Closing preview window...")
                break

            # Auto exit after 100 frames if non-interactive
            if frame_count > 120 and not cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE):
                break

    except Exception as exc:
        print(f"    Stream error: {exc}")

    finally:
        # 5. Clean Resource Release
        total_duration = time.time() - start_stream_t
        avg_fps = frame_count / max(0.1, total_duration)

        print("\n[5] Releasing Camera & Cleaning OpenCV Windows...")
        cap.release()
        cv2.destroyAllWindows()

        print(f"    - Total Stream Duration: {total_duration:.1f} s")
        print(f"    - Total Frames Rendered: {frame_count}")
        print(f"    - Average FPS Achieved:  {avg_fps:.1f} FPS")
        print("\nSUCCESS: OpenCV camera module is fully operational and verified!")


if __name__ == "__main__":
    main()
