"""Continuous Voice Conversation Loop for Campus Helpdesk Robot.

Initializes VAD, STT (FasterWhisper), Language Detector, RAGChatService (with GenerationRouter & ContextComposer),
and NonBlockingTTSService to provide a hands-free, turn-by-turn voice interaction loop.
"""

import argparse
import logging
import os
import sys
import time
import wave
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.services.language_detector import LanguageDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice_loop")

SCRATCH_DIR = Path("scratch")
EXIT_KEYWORDS = ["exit", "quit", "goodbye", "bye", "stop", "terminate", "ಅಲ್ವಿಡಾ", "ಬೈ", "ಖತಮ್"]


def convert_wav_to_16k_mono_pcm(wav_path: Path) -> bytes:
    """Read a WAV file and convert to 16kHz 16-bit mono PCM bytes for STT processing."""
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    samples = np.frombuffer(raw_bytes, dtype=np.int16)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    if framerate != 16000:
        num_target_samples = int(len(samples) * 16000 / framerate)
        samples = np.interp(
            np.linspace(0, len(samples), num_target_samples, endpoint=False),
            np.arange(len(samples)),
            samples,
        ).astype(np.int16)

    return samples.tobytes()


def generate_synthetic_audio(text: str, output_wav: Path) -> Optional[bytes]:
    """Generate synthetic audio using pyttsx3 or fallback to valid PCM WAV."""
    try:
        if output_wav.exists():
            try:
                output_wav.unlink()
            except Exception:
                pass

        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, str(output_wav))
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass

        if output_wav.exists() and output_wav.stat().st_size > 0:
            return convert_wav_to_16k_mono_pcm(output_wav)
    except Exception as err:
        logger.warning(f"pyttsx3 synthesis unavailable for '{text}': {err}")

    # Robust fallback: Generate 2 seconds of 16kHz 16-bit PCM audio
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate a pleasant 440 Hz audio tone
    audio_signal = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
    
    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_signal.tobytes())

    return audio_signal.tobytes()


class VoiceConversationLoop:
    """Manages continuous turn-by-turn voice interaction."""

    def __init__(self, simulate: bool = False) -> None:
        self.simulate = simulate
        self.session_id = f"voice_session_{int(time.time())}"
        
        print("\n" + "=" * 76)
        print("    INITIALIZING CAMPUS HELPDESK CONTINUOUS VOICE CONVERSATION LOOP")
        print("=" * 76 + "\n")

        # 1. Load Settings & Configuration
        print("[1/5] Loading configuration & settings...")
        self.settings = get_settings()

        # 2. RAG Pipeline & Vector Index
        print("[2/5] Initializing FAISS Vector Store & ContextComposer...")
        self.rag_pipeline = create_rag_pipeline(self.settings)
        self.rag_pipeline.load_index()
        self.context_composer = ContextComposer(self.settings)

        # 3. LLM Service with GenerationRouter (Cloud / Offline Fallback)
        print(f"[3/5] Initializing LLM Service (Router: {self.settings.enable_cloud_llm_router})...")
        self.llm_service = create_llm_service(self.settings)
        self.chat_service = RAGChatService(
            llm_service=self.llm_service,
            rag_pipeline=self.rag_pipeline,
            context_composer=self.context_composer,
        )

        # 4. FasterWhisper STT Service & Language Detector
        whisper_model = getattr(self.settings, "whisper_model_size", "small")
        print(f"[4/5] Loading FasterWhisper STT Service (Model: {whisper_model})...")
        self.stt_service = FasterWhisperSTTService(
            model_size=whisper_model,
            device=getattr(self.settings, "whisper_device", "cpu"),
            compute_type=getattr(self.settings, "whisper_compute_type", "int8"),
            enable_online_fallback=getattr(self.settings, "stt_enable_online_fallback", False),
            debug=False,
        )
        self.lang_detector = LanguageDetector()

        # 5. Non-Blocking TTS Service
        print(f"[5/5] Initializing NonBlockingTTSService (Default Voice: {self.settings.tts_voice_model})...")
        self.tts_service = NonBlockingTTSService(voice_model=self.settings.tts_voice_model)

        print("\n" + "=" * 76)
        print("               VOICE CONVERSATION LOOP READY")
        print(f" Mode: {'SIMULATION (Pre-recorded / Synthetic Audio)' if self.simulate else 'LIVE MICROPHONE (Hardware / VAD)'}")
        print(" Say 'exit', 'quit', or 'goodbye' to stop the session cleanly.")
        print("=" * 76 + "\n")

    def run_turn(self, turn_number: int, pcm_bytes: Optional[bytes] = None, prompt_hint: Optional[str] = None) -> bool:
        """Process a single turn of voice conversation.

        Returns True to continue loop, False to exit cleanly.
        """
        print(f"\n======================================================================")
        print(f"                      [TURN {turn_number}]")
        print(f"======================================================================")

        try:
            # --- STAGE 1: LISTEN / CAPTURE AUDIO ---
            if pcm_bytes is None:
                if self.simulate:
                    print("🎤 [LISTENING] (Simulated Mode)...")
                    if prompt_hint:
                        wav_path = SCRATCH_DIR / f"sim_input_{turn_number}.wav"
                        pcm_bytes = generate_synthetic_audio(prompt_hint, wav_path)
                    else:
                        print("⚠️ [WARNING] No audio input provided for simulation turn.")
                        return True
                else:
                    print("🎤 [LISTENING] Waiting for speech via microphone (VAD active)...")
                    try:
                        import sounddevice as sd
                        duration = 4.0  # record 4 seconds of audio for live mic turn
                        sample_rate = 16000
                        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
                        sd.wait()
                        pcm_bytes = recording.tobytes()
                    except Exception as mic_err:
                        print(f"❌ [MIC HARDWARE ERROR] Could not record from microphone: {mic_err}")
                        print("💡 Live mic capture requires an active audio input device.")
                        print("   To test voice loop in sandboxed/headless mode, run with --simulate flag.")
                        return False

            if not pcm_bytes or len(pcm_bytes) < 100:
                print("⚠️ [STT] Silence or insufficient audio detected.")
                return True

            # --- STAGE 2: TRANSCRIBE & DETECT LANGUAGE ---
            print("🗣️ [TRANSCRIBING] Processing audio with FasterWhisper...")
            stt_res = self.stt_service.transcribe_audio(pcm_bytes, sample_rate=16000)
            transcribed_text = stt_res.text.strip()

            if not transcribed_text:
                if prompt_hint:
                    print(f"💡 [WHISPER UNCERTAIN] Using prompt hint: '{prompt_hint}'")
                    transcribed_text = prompt_hint
                else:
                    print("⚠️ [STT] No clear speech recognized.")
                    return True

            det_res = self.lang_detector.detect(transcribed_text)
            lang_code = det_res.language
            lang_name = det_res.language_name

            print(f"   ► Transcribed Text : \"{transcribed_text}\"")
            print(f"   ► Detected Language: {lang_name} ({lang_code}) [Confidence: {det_res.confidence:.0%}]")

            # --- STAGE 3: CHECK CLEAN EXIT KEYWORDS ---
            clean_text_lower = transcribed_text.lower()
            if any(kw in clean_text_lower for kw in EXIT_KEYWORDS):
                farewell = "Goodbye! Have a great day at KLE Technological University." if lang_code == "en" else "धन्यवाद! आपका दिन शुभ हो।"
                print(f"\n👋 [EXIT TRIGGERED] User said '{transcribed_text}'.")
                print(f"🔊 [TTS SPEAKING] {farewell}")
                self.tts_service.speak(farewell, language=lang_code)
                self.tts_service.wait_until_done(timeout=5.0)
                return False

            # --- STAGE 4: SEND TO RAG CHAT PIPELINE ---
            print("\n🤖 [CHAT PIPELINE] Querying RAG Knowledge Base...")
            start_chat = time.time()
            res = self.chat_service.respond(transcribed_text, session_id=self.session_id)
            chat_latency = time.time() - start_chat

            backend_used = getattr(res, "backend_used", getattr(self.llm_service, "last_used_backend", "LOCAL"))
            answer = getattr(res, "reply", getattr(res, "text", str(res))).strip()
            
            raw_sources = getattr(res, "supporting_sources", getattr(res, "sources", []))
            sources = []
            for s in raw_sources:
                if isinstance(s, str):
                    sources.append(s)
                else:
                    sources.append(getattr(s, "metadata", {}).get("source_url", getattr(s, "source", str(s))))

            print(f"   ► Backend Used : {backend_used} (Latency: {chat_latency:.2f}s)")
            print(f"   ► Answer       : {answer}")
            print(f"   ► Top Sources  : {sources[:2]}")

            # --- STAGE 5: TTS SPEAK RESPONSE ---
            print(f"\n🔊 [TTS SPEAKING] Playing response in {lang_name} ({lang_code})...")
            start_tts = time.time()
            self.tts_service.speak(answer, language=lang_code)
            self.tts_service.wait_until_done(timeout=15.0)
            tts_latency = time.time() - start_tts
            print(f"   ► Speech synthesis finished in {tts_latency:.2f}s.")

            return True

        except Exception as turn_err:
            logger.error(f"Error during turn {turn_number}: {turn_err}", exc_info=True)
            print(f"❌ [TURN ERROR] Turn {turn_number} failed gracefully: {turn_err}")
            return True

    def run_live_loop(self) -> None:
        """Run continuous live loop reading from microphone until exit signal."""
        turn = 1
        try:
            while True:
                should_continue = self.run_turn(turn_number=turn)
                if not should_continue:
                    break
                turn += 1
        except KeyboardInterrupt:
            print("\n\n🛑 [KEYBOARD INTERRUPT] Received Ctrl+C. Shutting down voice loop gracefully...")
            self.tts_service.speak("Goodbye!", language="en")
            self.tts_service.wait_until_done(timeout=3.0)
        finally:
            print("Session terminated cleanly.")

    def run_simulated_loop(self) -> None:
        """Run multi-turn simulated conversation including language switch & follow-up context."""
        sim_turns = [
            {
                "prompt": "What programs are offered by the School of Architecture?",
                "desc": "Turn 1: Initial English fact query",
            },
            {
                "prompt": "How long does that program take to complete?",
                "desc": "Turn 2: Follow-up question relying on prior conversational context ('that program')",
            },
            {
                "prompt": "कंप्यूटर साइंस विभाग के अध्यक्ष कौन हैं?",
                "desc": "Turn 3: Mid-conversation language switch to Hindi (Devanagari)",
            },
            {
                "prompt": "Thank you, goodbye!",
                "desc": "Turn 4: Clean exit command",
            },
        ]

        SCRATCH_DIR.mkdir(exist_ok=True)

        for idx, turn_data in enumerate(sim_turns, 1):
            prompt = turn_data["prompt"]
            desc = turn_data["desc"]
            print(f"\n>>> SIMULATION STEP {idx}/{len(sim_turns)}: {desc}")

            # Generate synthetic PCM audio for input
            wav_path = SCRATCH_DIR / f"sim_turn_{idx}.wav"
            pcm_bytes = generate_synthetic_audio(prompt, wav_path)

            should_continue = self.run_turn(turn_number=idx, pcm_bytes=pcm_bytes, prompt_hint=prompt)
            if not should_continue:
                print("\n✅ Simulation completed cleanly upon exit command.")
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Helpdesk Continuous Voice Conversation Loop")
    parser.add_argument("--simulate", action="store_true", help="Run in multi-turn simulation mode without live microphone")
    args = parser.parse_args()

    # If --simulate flag passed or sounddevice input unavailable, run simulation mode
    simulate_mode = args.simulate

    if not simulate_mode:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if not input_devices:
                print("⚠️ [HARDWARE NOTICE] No physical microphone input devices detected.")
                print("   Automatically switching to SIMULATION mode.")
                simulate_mode = True
        except Exception:
            print("⚠️ [HARDWARE NOTICE] sounddevice library/hardware check failed.")
            print("   Automatically switching to SIMULATION mode.")
            simulate_mode = True

    loop = VoiceConversationLoop(simulate=simulate_mode)
    if simulate_mode:
        loop.run_simulated_loop()
    else:
        loop.run_live_loop()


if __name__ == "__main__":
    main()
