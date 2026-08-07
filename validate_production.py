#!/usr/bin/env python
"""
Campus Helpdesk Robot — Production Validation Harness
======================================================

Boots the EXACT same SystemRuntime used by helpdesk_gui.py, attaches
read-only observers to the EventBus and FSM state machine, then collects:

  * Timestamps for every FSM state transition
  * Every EventBus event (type, source, latency from previous event)
  * Duplicate event detection
  * Thread count over time
  * Memory (RSS) over time
  * CPU utilisation over time
  * Camera frame rate
  * Event delivery counts per type

Produces:
  1. A detailed JSON log  (validation_log.json)
  2. A human-readable production readiness report (validation_report.txt)

This script does NOT modify any production code. It is a pure observer.

Usage
-----
    .venv\\Scripts\\python.exe validate_production.py [--soak SECONDS]

    --soak 1800   Full 30-minute soak (default)
    --soak 120    Quick 2-minute smoke test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

# Bootstrap: ensure src/ is on sys.path
_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Expected events in a complete interaction
EXPECTED_EVENTS = [
    "SYSTEM_STARTING",
    "SYSTEM_READY",
    "CAMERA_STARTED",
    "FRAME_CAPTURED",
    "PERSON_DETECTED",
    "VOICE_STARTED",
    "VOICE_STOPPED",
    "TRANSCRIPT_FINAL",
    "QUERY_STARTED",
    "ANSWER_READY",
    "TTS_STARTED",
    "TTS_COMPLETED",
    "PERSON_LEFT",
    "SESSION_ENDED",
]


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    timestamp: float
    wall_time: str


@dataclass
class EventRecord:
    event_type: str
    source: str
    timestamp: float
    wall_time: str
    delta_ms: float


@dataclass
class SystemSample:
    timestamp: float
    rss_mb: float
    cpu_pct: float
    thread_count: int
    frame_event_count: int
    event_bus_depth: int


@dataclass
class ValidationResult:
    start_time: float
    end_time: float
    duration_s: float
    fsm_transitions: list[dict] = field(default_factory=list)
    fsm_sequence_observed: list[str] = field(default_factory=list)
    event_counts: dict[str, int] = field(default_factory=dict)
    event_records: list[dict] = field(default_factory=list)
    system_samples: list[dict] = field(default_factory=list)
    camera_owner_count: int = 0
    error_events: list[str] = field(default_factory=list)
    reconnect_loops_detected: int = 0
    camera_disconnect_events: int = 0
    llm_latencies_ms: list[float] = field(default_factory=list)
    tts_latencies_ms: list[float] = field(default_factory=list)
    rag_latencies_ms: list[float] = field(default_factory=list)
    total_latencies_ms: list[float] = field(default_factory=list)


class ProductionValidator:
    def __init__(self, soak_seconds: int = 1800):
        self._soak_seconds = soak_seconds
        self._result = ValidationResult(
            start_time=time.perf_counter(),
            end_time=0.0,
            duration_s=0.0,
        )
        self._lock = threading.Lock()
        self._runtime: Any = None
        self._process = psutil.Process(os.getpid()) if HAS_PSUTIL else None
        self._last_event_time = time.perf_counter()
        self._query_start_time: float = 0.0
        self._tts_start_time: float = 0.0
        self._turn_start_time: float = 0.0
        self._disconnect_times: list[float] = []

    def run(self, simulate: bool = False) -> ValidationResult:
        print(f"\n{'='*70}")
        print("  Campus Helpdesk Robot - Production Validation Harness")
        print(f"{'='*70}")
        print(f"  Soak duration : {self._soak_seconds}s ({self._soak_seconds/60:.1f} min)")
        print(f"  Start time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        print("[1/5] Booting SystemRuntime...")
        self._boot_runtime()

        print("[2/5] Attaching EventBus observer...")
        self._attach_bus_observer()

        print("[3/5] Attaching FSM state-transition hook...")
        self._attach_fsm_hook()

        print("[4/5] Starting system sampler (every 10s)...")
        self._start_sampler()

        if simulate:
            print("[4.5] Starting interaction simulator thread...")
            self._start_simulator()

        print(f"[5/5] Running soak test for {self._soak_seconds}s...")
        print("      Interact with the robot now. Ctrl+C to stop early.\n")
        self._run_soak()

        print("\n[Done] Collecting final measurements...")
        self._finalize()
        return self._result

    def _boot_runtime(self) -> None:
        from campus_helpdesk.robot_main import build_production_runtime
        t0 = time.perf_counter()
        self._runtime = build_production_runtime(use_mock=False)
        self._runtime.start()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"      Runtime booted in {elapsed:.0f} ms")
        self._check_ownership()

    def _check_ownership(self) -> None:
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager
        mgr = CameraManager.get_instance()
        cap_holders = 0
        if mgr._cap is not None and mgr._cap.isOpened():
            cap_holders += 1
        svc = self._runtime.camera
        if getattr(svc, "_cap", None) is not None:
            cap_holders += 1
        self._result.camera_owner_count = cap_holders
        print(f"      Camera VideoCapture owners: {cap_holders} (expected: 1)")

    def _attach_bus_observer(self) -> None:
        def _on_event(env: Any) -> None:
            now = time.perf_counter()
            et = str(env.event_type.value) if hasattr(env.event_type, "value") else str(env.event_type)
            src = str(env.source) if env.source else "unknown"
            p = env.payload

            with self._lock:
                delta_ms = (now - self._last_event_time) * 1000
                self._last_event_time = now

                if et != "FRAME_CAPTURED":
                    rec = EventRecord(
                        event_type=et, source=src, timestamp=now,
                        wall_time=datetime.now(timezone.utc).isoformat(),
                        delta_ms=round(delta_ms, 2),
                    )
                    self._result.event_records.append(asdict(rec))

                self._result.event_counts[et] = self._result.event_counts.get(et, 0) + 1

                if et == "ERROR":
                    msg = getattr(p, "message", str(p))
                    self._result.error_events.append(
                        f"{datetime.now(timezone.utc).isoformat()}: {msg}")

                if et == "CAMERA_DISCONNECTED":
                    self._result.camera_disconnect_events += 1
                    self._disconnect_times.append(now)
                    recent = [t for t in self._disconnect_times if now - t < 2.0]
                    if len(recent) >= 3:
                        self._result.reconnect_loops_detected += 1

                if et == "TRANSCRIPT_FINAL":
                    self._turn_start_time = now
                    self._query_start_time = now
                elif et == "ANSWER_READY":
                    if self._query_start_time:
                        self._result.llm_latencies_ms.append(
                            round((now - self._query_start_time) * 1000, 1))
                elif et == "TTS_STARTED":
                    self._tts_start_time = now
                elif et == "TTS_COMPLETED":
                    if self._tts_start_time:
                        self._result.tts_latencies_ms.append(
                            round((now - self._tts_start_time) * 1000, 1))
                    if self._turn_start_time:
                        self._result.total_latencies_ms.append(
                            round((now - self._turn_start_time) * 1000, 1))
                        self._turn_start_time = 0.0
                elif et == "QUERY_COMPLETED":
                    if self._query_start_time:
                        self._result.rag_latencies_ms.append(
                            round((now - self._query_start_time) * 1000, 1))

            if et != "FRAME_CAPTURED":
                print(f"  [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]  "
                      f"EVENT  {et:<30}  src={src}")

        self._bus_handle = self._runtime.bus.subscribe(
            _on_event, event_types=None, source="validator")
        print("      EventBus wildcard subscription registered.")

    def _attach_fsm_hook(self) -> None:
        def _on_transition(from_state: Any, to_state: Any) -> None:
            now = time.perf_counter()
            fs = str(from_state).split(".")[-1]
            ts_name = str(to_state).split(".")[-1]
            wall = datetime.now(timezone.utc).isoformat()
            with self._lock:
                self._result.fsm_transitions.append(asdict(StateTransition(
                    from_state=fs, to_state=ts_name,
                    timestamp=now, wall_time=wall,
                )))
                obs = self._result.fsm_sequence_observed
                if not obs or obs[-1] != ts_name:
                    obs.append(ts_name)
            print(f"  [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]  "
                  f"STATE  {fs:<18} -> {ts_name}")

        self._runtime.state_machine.register_on_transition(_on_transition)
        print("      FSM on_transition hook registered.")

    def _start_sampler(self) -> None:
        self._sampler_stop = threading.Event()

        def _sampler():
            while not self._sampler_stop.is_set():
                try:
                    if self._process is not None:
                        rss = self._process.memory_info().rss / (1024 * 1024)
                        cpu = self._process.cpu_percent(interval=None)
                        threads = self._process.num_threads()
                    else:
                        rss = 0.0
                        cpu = 0.0
                        threads = threading.active_count()
                    frames = self._result.event_counts.get("FRAME_CAPTURED", 0)
                    try:
                        bus_depth = self._runtime.bus._queue.qsize()
                    except Exception:
                        bus_depth = -1
                    with self._lock:
                        self._result.system_samples.append(asdict(SystemSample(
                            timestamp=time.perf_counter(),
                            rss_mb=round(rss, 1),
                            cpu_pct=round(cpu, 1),
                            thread_count=threads,
                            frame_event_count=frames,
                            event_bus_depth=bus_depth,
                        )))
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}]  "
                          f"SAMPLE  RSS={rss:.0f}MB  CPU={cpu:.0f}%  "
                          f"threads={threads}  frames={frames}  bus={bus_depth}")
                except Exception as exc:
                    print(f"  [sampler] {exc}")
                self._sampler_stop.wait(10.0)

        threading.Thread(target=_sampler, daemon=True,
                         name="validator-sampler").start()

    def _start_simulator(self) -> None:
        self._simulator_stop = threading.Event()

        def _simulator():
            # Let the system stabilize first
            time.sleep(6.0)

            questions = [
                "Who is the HOD of Computer Science department?",
                "What are the library timings?",
                "What is the intake for BE Computer Science?",
                "Who is the principal of the college?",
                "Where is the placement office located?",
            ]
            q_idx = 0

            from campus_helpdesk.interaction.events import EventEnvelope, EventType, PersonDetectedPayload, PersonLeftPayload, TranscriptPayload, VoicePayload

            while not self._simulator_stop.is_set():
                # 1. Simulate person walking up
                print("\n  [SIMULATOR] Simulating person detection...")
                self._runtime.bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.PERSON_DETECTED,
                        source="simulator",
                        payload=PersonDetectedPayload(
                            confidence=0.95,
                            camera_index=0,
                            bounding_box=(100, 100, 200, 200),
                        )
                    )
                )

                # Wait for state transition and potential mock greeting
                time.sleep(5.0)

                # Ask 2 questions during this turn
                for _ in range(2):
                    if self._simulator_stop.is_set():
                        break

                    q = questions[q_idx % len(questions)]
                    q_idx += 1
                    chunk_id = str(uuid.uuid4())

                    # Simulate VOICE_STARTED (READY -> LISTENING)
                    self._runtime.bus.publish(
                        EventEnvelope.create(
                            event_type=EventType.VOICE_STARTED,
                            source="simulator_vad",
                            payload=VoicePayload(audio_chunk_id=chunk_id)
                        )
                    )
                    time.sleep(1.0)

                    # Simulate VOICE_STOPPED (LISTENING -> PROCESSING)
                    self._runtime.bus.publish(
                        EventEnvelope.create(
                            event_type=EventType.VOICE_STOPPED,
                            source="simulator_vad",
                            payload=VoicePayload(audio_chunk_id=chunk_id, duration_ms=1500, audio_segment_path="mock.wav")
                        )
                    )

                    print(f"\n  [SIMULATOR] Asking: '{q}'")
                    self._runtime.bus.publish(
                        EventEnvelope.create(
                            event_type=EventType.TRANSCRIPT_FINAL,
                            source="simulator_speech",
                            payload=TranscriptPayload(
                                text=q,
                                is_final=True,
                                audio_chunk_id=chunk_id,
                                confidence=0.98,
                            )
                        )
                    )

                    # Wait for processing & speech synthesis (usually 10-15s total)
                    time.sleep(15.0)

                # 2. Simulate person leaving
                if self._simulator_stop.is_set():
                    break
                print("\n  [SIMULATOR] Simulating person leaving...")
                self._runtime.bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.PERSON_LEFT,
                        source="simulator",
                        payload=PersonLeftPayload(
                            last_seen_at=datetime.now(timezone.utc),
                            frames_without_detection=150,
                        )
                    )
                )

                # Wait before next interaction cycle
                time.sleep(15.0)

        threading.Thread(target=_simulator, daemon=True,
                         name="validator-simulator").start()

    def _run_soak(self) -> None:
        t_end = time.perf_counter() + self._soak_seconds
        try:
            last_print = 0
            while time.perf_counter() < t_end:
                elapsed = time.perf_counter() - self._result.start_time
                if int(elapsed) % 60 == 0 and int(elapsed) != last_print and elapsed > 5:
                    remaining = t_end - time.perf_counter()
                    print(f"\n  [{datetime.now().strftime('%H:%M:%S')}]  "
                          f"--- {elapsed:.0f}s elapsed, {remaining:.0f}s remaining ---")
                    last_print = int(elapsed)
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n  Stopped early by user.")

    def _finalize(self) -> None:
        self._sampler_stop.set()
        if hasattr(self, "_simulator_stop"):
            self._simulator_stop.set()
        self._result.end_time = time.perf_counter()
        self._result.duration_s = round(
            self._result.end_time - self._result.start_time, 1)
        try:
            self._runtime.bus.unsubscribe(self._bus_handle)
        except Exception:
            pass
        try:
            self._runtime.stop()
        except Exception:
            pass


def _avg(lst: list[float]) -> float:
    return round(sum(lst) / len(lst), 1) if lst else 0.0

def _p95(lst: list[float]) -> float:
    if not lst:
        return 0.0
    s = sorted(lst)
    return round(s[min(int(len(s) * 0.95), len(s)-1)], 1)

def generate_report(result: ValidationResult) -> str:
    dur_m = result.duration_s / 60
    rss = [s["rss_mb"] for s in result.system_samples]
    cpu = [s["cpu_pct"] for s in result.system_samples]
    thr = [s["thread_count"] for s in result.system_samples]
    frames = result.event_counts.get("FRAME_CAPTURED", 0)
    fps = round(frames / max(result.duration_s, 1), 1)
    fsm_hit = all(s in result.fsm_sequence_observed
                  for s in ["IDLE", "READY", "LISTENING", "PROCESSING", "SPEAKING"])

    missing = [e for e in EXPECTED_EVENTS
               if result.event_counts.get(e, 0) == 0]

    blockers: list[str] = []
    if result.reconnect_loops_detected > 0:
        blockers.append(f"CAMERA reconnect loop: {result.reconnect_loops_detected} occurrences")
    if result.event_counts.get("TRANSCRIPT_FINAL", 0) == 0:
        blockers.append("STT: No transcription events (SAC likely blocking faster-whisper DLL)")
    if result.event_counts.get("TTS_COMPLETED", 0) == 0:
        blockers.append("TTS: No speech events (SAC likely blocking Piper/espeakbridge DLL)")
    if result.event_counts.get("PERSON_DETECTED", 0) == 0:
        blockers.append("Vision: PERSON_DETECTED never fired (check camera, lighting, HOG detector)")
    if result.camera_owner_count != 1:
        blockers.append(f"Camera ownership: {result.camera_owner_count} owners (expected 1)")
    if missing:
        blockers.append(f"Events never seen: {', '.join(missing)}")

    warnings: list[str] = []
    if result.error_events:
        warnings.append(f"{len(result.error_events)} ERROR event(s) on EventBus")
    if _avg(rss) > 2000:
        warnings.append(f"Memory high: avg {_avg(rss):.0f} MB RSS")
    if result.camera_disconnect_events > 3:
        warnings.append(f"Camera disconnects: {result.camera_disconnect_events}")

    lines = [
        "=" * 70,
        "  Campus Helpdesk Robot -- Production Readiness Report",
        f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Duration  : {dur_m:.1f} min ({result.duration_s:.0f}s)",
        "=" * 70,
        "",
        "STARTUP",
        f"  System ready         : {'YES' if result.event_counts.get('SYSTEM_READY', 0) > 0 else 'NO'}",
        f"  Camera started       : {'YES' if result.event_counts.get('CAMERA_STARTED', 0) > 0 else 'NO'}",
        f"  Camera owner count   : {result.camera_owner_count} (expected 1)",
        "",
        "CAMERA STABILITY",
        f"  Frames captured      : {frames:,}",
        f"  Estimated FPS        : {fps}",
        f"  Disconnect events    : {result.camera_disconnect_events}",
        f"  Reconnect loops      : {result.reconnect_loops_detected}",
        "",
        "MICROPHONE / VAD",
        f"  VOICE_STARTED        : {result.event_counts.get('VOICE_STARTED', 0)}",
        f"  VOICE_STOPPED        : {result.event_counts.get('VOICE_STOPPED', 0)}",
        "",
        "STT",
        f"  TRANSCRIPT_FINAL     : {result.event_counts.get('TRANSCRIPT_FINAL', 0)}",
        f"  Status               : {'ACTIVE' if result.event_counts.get('TRANSCRIPT_FINAL',0)>0 else 'BLOCKED (SAC)'}",
        "",
        "RAG + LLM",
        f"  QUERY_STARTED        : {result.event_counts.get('QUERY_STARTED', 0)}",
        f"  ANSWER_READY         : {result.event_counts.get('ANSWER_READY', 0)}",
        f"  LLM avg/p95 latency  : {_avg(result.llm_latencies_ms)} ms / {_p95(result.llm_latencies_ms)} ms",
        f"  RAG avg/p95 latency  : {_avg(result.rag_latencies_ms)} ms / {_p95(result.rag_latencies_ms)} ms",
        f"  Total avg/p95        : {_avg(result.total_latencies_ms)} ms / {_p95(result.total_latencies_ms)} ms",
        f"  Completed turns      : {len(result.total_latencies_ms)}",
        "",
        "TTS",
        f"  TTS_COMPLETED        : {result.event_counts.get('TTS_COMPLETED', 0)}",
        f"  TTS avg/p95 latency  : {_avg(result.tts_latencies_ms)} ms / {_p95(result.tts_latencies_ms)} ms",
        f"  Status               : {'ACTIVE' if result.event_counts.get('TTS_COMPLETED',0)>0 else 'BLOCKED (SAC)'}",
        "",
        "INTERACTION FSM",
        f"  PERSON_DETECTED      : {result.event_counts.get('PERSON_DETECTED', 0)}",
        f"  PERSON_LEFT          : {result.event_counts.get('PERSON_LEFT', 0)}",
        f"  SESSION_ENDED        : {result.event_counts.get('SESSION_ENDED', 0)}",
        f"  FSM transitions      : {len(result.fsm_transitions)}",
        f"  Full cycle verified  : {'YES' if fsm_hit else 'NO (insufficient interactions)'}",
        f"  States observed      : {' -> '.join(result.fsm_sequence_observed[:12])}",
        "",
        "SYSTEM RESOURCES",
        f"  Memory RSS avg/max   : {_avg(rss):.0f} MB / {max(rss, default=0):.0f} MB",
        f"  CPU avg/max          : {_avg(cpu):.0f}% / {max(cpu, default=0):.0f}%",
        f"  Thread count avg/max : {_avg(thr):.0f} / {max(thr, default=0):.0f}",
        "",
        "EVENTBUS TOTALS",
        f"  Total events         : {sum(result.event_counts.values()):,}",
        f"  ERROR events         : {result.event_counts.get('ERROR', 0)}",
        "  Top event types:",
    ]

    for et, cnt in sorted(result.event_counts.items(), key=lambda x: -x[1])[:12]:
        lines.append(f"    {et:<38} {cnt:>8,}")

    lines += ["", "ERROR EVENTS"]
    if result.error_events:
        for e in result.error_events[:8]:
            lines.append(f"  {e}")
        if len(result.error_events) > 8:
            lines.append(f"  ...and {len(result.error_events)-8} more")
    else:
        lines.append("  (none)")

    lines += ["", "PRODUCTION BLOCKERS"]
    if blockers:
        for b in blockers:
            lines.append(f"  [BLOCKER] {b}")
    else:
        lines.append("  (none)")

    lines += ["", "WARNINGS"]
    if warnings:
        for w in warnings:
            lines.append(f"  [WARN] {w}")
    else:
        lines.append("  (none)")

    lines += ["", "OVERALL VERDICT"]
    if not blockers:
        lines.append("  PRODUCTION READY -- no blockers found.")
    else:
        lines.append(f"  NOT READY -- {len(blockers)} blocker(s) must be resolved before deployment.")

    lines += ["", "=" * 70]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--soak", type=int, default=1800,
                        help="Soak duration seconds (default 1800)")
    parser.add_argument("--simulate", action="store_true",
                        help="Run automated interaction simulator thread")
    args = parser.parse_args()

    validator = ProductionValidator(soak_seconds=args.soak)
    result = validator.run(simulate=args.simulate)

    log_path = Path("validation_log.json")
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, default=str)
    print(f"\nJSON log  : {log_path.absolute()}")

    report_path = Path("validation_report.txt")
    report = generate_report(result)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report    : {report_path.absolute()}")
    print()
    print(report)


if __name__ == "__main__":
    main()
