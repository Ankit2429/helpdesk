"""
run_pi_full_evaluation.py
Full End-to-End Evaluation Suite:
1. 10-question English RAG Suite (Accuracy + Latency)
2. 10-question Kannada Canned-FAQ Suite (100% Deterministic + WAV Cache Latency)
3. 5-question Natural Spoken Audio Loop (Whisper STT, RAG/FAQ TTT, TTS Latency)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import types
import time
import os

av_mock = types.ModuleType("av")
av_mock.__spec__ = types.SimpleNamespace(origin="mock")
sys.modules["av"] = av_mock

from ttt_service import TTTService, CANNED_FAQ
from tts_service import TTSService, SAMPLE_RATE
from stt_service import STTService
from test_rag_consistency import TEST_SUITE as ENGLISH_RAG_SUITE

KANNADA_TEST_SUITE = [
    ("Q1", "ಗ್ರಂಥಾಲಯವು ಕ್ಯಾಂಪಸ್‌ನಲ್ಲಿ ಎಲ್ಲಿದೆ?", "Where is the library located in campus?", CANNED_FAQ["kn"]["library_location"]),
    ("Q2", "ಗ್ರಂಥಾಲಯವು ಯಾವಾಗ ತೆರೆದಿರುತ್ತದೆ?", "When is the library open?", CANNED_FAQ["kn"]["library_hours"]),
    ("Q3", "ವಾರಾಂತ್ಯದಲ್ಲಿ ಗ್ರಂಥಾಲಯದ ಸಮಯ ಏನು?", "What are the library hours on weekends?", CANNED_FAQ["kn"]["library_hours"]),
    ("Q4", "ಗ್ರಂಥಾಲಯದ ಇಮೇಲ್ ವಿಳಾಸ ಏನು?", "What is the email address for the library?", CANNED_FAQ["kn"]["library_email"]),
    ("Q5", "ಗ್ರಂಥಾಲಯದ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?", "What is the library phone number?", CANNED_FAQ["kn"]["library_phone"]),
    ("Q6", "ಅಡ್ಮಿಷನ್ ಕಚೇರಿ ಎಲ್ಲಿದೆ?", "Where is the admissions office located?", CANNED_FAQ["kn"]["admissions_location"]),
    ("Q7", "ಅಡ್ಮಿಷನ್ ಕಚೇರಿಯ ಸಮಯ ಏನು?", "What are the admissions office hours?", CANNED_FAQ["kn"]["admissions_hours"]),
    ("Q8", "ಅಡ್ಮಿಷನ್ ಕಚೇರಿಯ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?", "What is the admissions office phone number?", CANNED_FAQ["kn"]["fallback"]),
    ("Q9", "ನಾನು ಪ್ರವೇಶ ಪಡೆಯುವುದು ಹೇಗೆ?", "How can I get admitted?", CANNED_FAQ["kn"]["admissions_process"]),
    ("Q10", "ಕೆಫೆಟೇರಿಯಾದ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?", "What is the cafeteria's phone number?", CANNED_FAQ["kn"]["fallback"]),
]

SPOKEN_SUITE = [
    ("Q1", "Where's the library located on campus?", "Where is the library located in campus?"),
    ("Q2", "What time does the library open today?", "When is the library open?"),
    ("Q6", "Where can I find the admissions office?", "Where is the admissions office located?"),
    ("Q8", "What is the admissions office phone number?", "What is the admissions office phone number?"),
    ("Q9", "How do I apply for admission at the college?", "How can I get admitted?"),
]


def run_english_rag(ttt):
    print("\n=======================================================================")
    print("      PART 1: 10-QUESTION ENGLISH RAG TEST SUITE")
    print("=======================================================================")
    
    pass_count = 0
    en_results = []

    for test in ENGLISH_RAG_SUITE:
        q_id = test["id"]
        q_text = test["question"]
        verifier = test["verifier"]
        
        t0 = time.time()
        reply = ttt.get_reply(q_text, language="en")
        elapsed = time.time() - t0

        passed, reason = verifier(reply)
        if passed:
            pass_count += 1

        en_results.append({
            "id": q_id,
            "question": q_text,
            "reply": reply,
            "elapsed": elapsed,
            "passed": passed,
            "reason": reason,
        })
        print(f"[{q_id}] ({elapsed:.2f}s) {'PASSED ✓' if passed else 'FAILED ✗'} | Query: \"{q_text}\"")

    print(f"\nEnglish RAG Score: {pass_count}/10 Passed. Avg Latency: {sum(r['elapsed'] for r in en_results)/len(en_results):.2f}s")
    return en_results


def run_kannada_canned(ttt, tts):
    print("\n=======================================================================")
    print("      PART 2: 10-QUESTION KANNADA CANNED-FAQ SUITE")
    print("=======================================================================")

    kn_results = []
    pass_count = 0

    for q_id, q_kn, q_en, expected in KANNADA_TEST_SUITE:
        t0 = time.time()
        reply = ttt.get_reply(q_kn, language="kn")
        t_ttt = (time.time() - t0) * 1000

        t1 = time.time()
        audio = tts.synthesize(reply, language="kn")
        t_tts = (time.time() - t1) * 1000

        passed = (reply == expected)
        if passed:
            pass_count += 1

        kn_results.append({
            "id": q_id,
            "query": q_kn,
            "reply": reply,
            "ttt_ms": t_ttt,
            "tts_ms": t_tts,
            "passed": passed,
        })
        print(f"[{q_id}] (TTT: {t_ttt:.1f}ms, TTS: {t_tts:.2f}ms) {'PASSED ✓' if passed else 'FAILED ✗'} | \"{q_kn}\"")

    print(f"\nKannada Canned FAQ Score: {pass_count}/10 Passed. Avg TTT: {sum(r['ttt_ms'] for r in kn_results)/len(kn_results):.1f}ms, Avg TTS: {sum(r['tts_ms'] for r in kn_results)/len(kn_results):.2f}ms")
    return kn_results


def run_spoken_pipeline(stt, ttt, tts):
    print("\n=======================================================================")
    print("      PART 3: 5-QUESTION NATURAL SPOKEN AUDIO PIPELINE TEST")
    print("=======================================================================")

    spoken_results = []

    for q_id, spoken_text, orig_q in SPOKEN_SUITE:
        # Generate spoken audio sample
        synth_audio = tts.synthesize(spoken_text, language="en")
        
        # 1. STT Stage
        t0 = time.time()
        stt_res = stt.transcribe_audio(synth_audio)
        t_stt = time.time() - t0
        transcription = stt_res.get("text", "")

        # 2. TTT Stage
        t1 = time.time()
        reply = ttt.get_reply(transcription, language="en")
        t_ttt = time.time() - t1

        # 3. TTS Stage
        t2 = time.time()
        out_audio = tts.synthesize(reply, language="en")
        t_tts = time.time() - t2

        spoken_results.append({
            "id": q_id,
            "spoken": spoken_text,
            "stt_text": transcription,
            "reply": reply,
            "stt_sec": t_stt,
            "ttt_sec": t_ttt,
            "tts_sec": t_tts,
        })
        print(f"[{q_id}] STT: \"{transcription}\" ({t_stt:.2f}s) | TTT: ({t_ttt:.2f}s) | TTS: ({t_tts*1000:.1f}ms)")
        print(f"     Reply: \"{reply}\"")

    return spoken_results


def main():
    print("\n=======================================================================")
    print("       FULL RASPBERRY PI SYSTEM COMPREHENSIVE BENCHMARK EVALUATION")
    print("=======================================================================")

    stt = STTService()
    ttt = TTTService()
    tts = TTSService()

    en_res = run_english_rag(ttt)
    kn_res = run_kannada_canned(ttt, tts)
    sp_res = run_spoken_pipeline(stt, ttt, tts)

    print("\n" + "=" * 75)
    print("                   FINAL SYSTEM BENCHMARK SUMMARY")
    print("=" * 75)
    print(f"1. English RAG 10-Question Suite : {sum(1 for r in en_res if r['passed'])}/10 Passed (Avg Latency: {sum(r['elapsed'] for r in en_res)/len(en_res):.2f}s)")
    print(f"2. Kannada Canned FAQ 10-Suite   : {sum(1 for r in kn_res if r['passed'])}/10 Passed (Avg TTS: {sum(r['tts_ms'] for r in kn_res)/len(kn_res):.2f}ms)")
    print(f"3. Spoken Audio 5-Question Loop  : STT Avg={sum(r['stt_sec'] for r in sp_res)/len(sp_res):.2f}s | TTT Avg={sum(r['ttt_sec'] for r in sp_res)/len(sp_res):.2f}s | TTS Avg={sum(r['tts_sec']*1000 for r in sp_res)/len(sp_res):.1f}ms")
    print("=" * 75)

if __name__ == "__main__":
    main()
