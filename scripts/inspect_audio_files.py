"""Technical Analysis & Inspection of Synthesized Audio Artifacts."""

from pathlib import Path
import wave
import numpy as np


def analyze_wav_file(wav_path: Path) -> dict:
    """Analyze technical audio properties of a WAV file."""
    if not wav_path.exists():
        return {"error": f"File does not exist: {wav_path}"}

    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    duration_sec = n_frames / float(framerate) if framerate > 0 else 0.0
    bit_depth = sampwidth * 8

    # Parse PCM 16-bit samples
    if sampwidth == 2:
        audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
        max_possible_val = 32768.0
    elif sampwidth == 1:
        audio_data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) * 256.0
        max_possible_val = 32768.0
    else:
        audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
        max_possible_val = 32768.0

    if len(audio_data) == 0:
        return {"error": "Empty audio data"}

    # Reshape channels if stereo
    if n_channels > 1:
        audio_data = audio_data.reshape(-1, n_channels)[:, 0]  # channel 0

    abs_samples = np.abs(audio_data.astype(np.float64))
    peak_val = np.max(abs_samples)
    peak_db = 20 * np.log10(peak_val / max_possible_val) if peak_val > 0 else -100.0

    rms_val = np.sqrt(np.mean(np.square(audio_data.astype(np.float64))))
    rms_db = 20 * np.log10(rms_val / max_possible_val) if rms_val > 0 else -100.0

    # Calculate active speech ratio (non-silence threshold: > -40 dB or > 1% peak)
    noise_threshold = max(200.0, 0.01 * peak_val)
    non_silent_samples = np.sum(abs_samples > noise_threshold)
    speech_activity_ratio = (non_silent_samples / len(audio_data)) * 100.0 if len(audio_data) > 0 else 0.0

    is_silent = rms_val < 50.0 or speech_activity_ratio < 1.0
    is_clipping = peak_val >= 32766.0

    return {
        "filename": wav_path.name,
        "file_size_bytes": wav_path.stat().st_size,
        "duration_sec": round(duration_sec, 2),
        "sample_rate_hz": framerate,
        "channels": "Mono" if n_channels == 1 else f"Stereo ({n_channels})",
        "bit_depth": f"{bit_depth}-bit",
        "peak_amplitude_ratio": round(float(peak_val / max_possible_val), 3),
        "peak_amplitude_db": round(float(peak_db), 1),
        "rms_level_db": round(float(rms_db), 1),
        "active_speech_pct": round(float(speech_activity_ratio), 1),
        "is_silent": is_silent,
        "is_clipping": is_clipping,
    }


def main() -> None:
    outputs_dir = Path("outputs")
    files = sorted(list(outputs_dir.glob("*.wav")))

    if not files:
        files = [
            Path("outputs/full_pipeline_en_q1.wav"),
            Path("outputs/full_pipeline_hi_q2.wav"),
            Path("outputs/full_pipeline_kn_q3.wav"),
        ]

    print("\n" + "=" * 90)
    print("TECHNICAL AUDIO QUALITY & SPECIFICATION ANALYSIS")
    print("=" * 90 + "\n")

    header = f"{'Filename':<26} | {'Duration':<9} | {'Sample Rate':<12} | {'Channels':<8} | {'Bit Depth':<10} | {'Peak dB':<8} | {'RMS dB':<8} | {'Speech %':<9} | {'Status'}"
    print(header)
    print("-" * len(header))

    for f in files:
        stats = analyze_wav_file(f)
        if "error" in stats:
            print(f"{f.name:<26} | ERROR: {stats['error']}")
            continue

        status = "OK (Clean)"
        if stats["is_silent"]:
            status = "SILENT (Corrupted)"
        elif stats["is_clipping"]:
            status = "CLIPPING (Distorted)"

        print(
            f"{stats['filename']:<26} | "
            f"{stats['duration_sec']}s{'' :<4} | "
            f"{stats['sample_rate_hz']} Hz{'' :<3} | "
            f"{stats['channels']:<8} | "
            f"{stats['bit_depth']:<10} | "
            f"{stats['peak_amplitude_db']} dB{'' :<2} | "
            f"{stats['rms_level_db']} dB{'' :<2} | "
            f"{stats['active_speech_pct']}%{'' :<4} | "
            f"{status}"
        )

    print("-" * len(header) + "\n")


if __name__ == "__main__":
    main()
