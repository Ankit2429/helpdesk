# Pan/Tilt Head-Tracking Hardware Integration Guide

## Overview

The `PersonDetector` module in `src/campus_helpdesk/infrastructure/vision/person_detector.py` calculates and exposes the normalized 2D center position `(face_center)` of the primary detected face in real-time.

---

## Data Contract

`PersonDetector.detect_in_frame(frame)` returns a `DetectionResult` object containing:

```python
class DetectionResult(tuple):
    person_detected: bool
    annotated_frame: np.ndarray
    face_center: tuple[float, float] | None  # (norm_x, norm_y) from 0.0 to 1.0
```

- **`norm_x`**: `0.0` (Left boundary) -> `0.5` (Dead Center) -> `1.0` (Right boundary)
- **`norm_y`**: `0.0` (Top boundary) -> `0.5` (Dead Center) -> `1.0` (Bottom boundary)

---

## Hardware Interface Architecture (Servos / Motors)

When connecting pan/tilt servo motors (e.g. Arduino, ESP32, or Serial PWM Controller):

```
Camera Frame (OpenCV)
       ↓
PersonDetector.detect_in_frame()
       ↓
DetectionResult.face_center (norm_x, norm_y)
       ↓
PID Controller / Servo Driver (Serial / I2C)
       ↓
Pan Motor (Yaw Angle) & Tilt Motor (Pitch Angle)
```

### Example Servo Mapping Pseudo-code

```python
def update_head_position(face_center: tuple[float, float], current_pan: float, current_tilt: float):
    if face_center is None:
        return  # Maintain current orientation or return to home (0.5, 0.5)

    norm_x, norm_y = face_center

    # Proportional Error relative to dead center (0.5, 0.5)
    error_x = norm_x - 0.5
    error_y = norm_y - 0.5

    # Adjust servo angles
    kp = 15.0  # Proportional gain
    target_pan = current_pan - (error_x * kp)
    target_tilt = current_tilt + (error_y * kp)

    # Clamp servo angles to physical limits [0°, 180°]
    target_pan = max(0.0, min(180.0, target_pan))
    target_tilt = max(0.0, min(180.0, target_tilt))

    # Send PWM command over Serial to Servo Controller
    send_servo_command(pan=target_pan, tilt=target_tilt)
```
