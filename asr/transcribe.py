import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import json
import re
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
FILLERS = re.compile(
    r"\b(um+|uh+|like|you know|sort of|kind of|i mean|ah|erm)\b",
    re.IGNORECASE
)

_MODEL = None

def get_model(model_size="small"):
    global _MODEL
    if _MODEL is None:
        print(f"Loading Whisper '{model_size}' model...")
        _MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODEL

def record_audio(turn=1):
    os.makedirs("recordings", exist_ok=True)
    filename = f"recordings/recording_turn{turn}.wav"
    print("Press Enter to start recording...")
    input()
    print("Recording... Press Enter to stop.")
    chunks = []
    def callback(indata, frames, time, status):
        chunks.append(indata.copy())
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype='float32', callback=callback):
        input()
    audio = np.concatenate(chunks, axis=0)
    sf.write(filename, audio, SAMPLE_RATE)
    print(f"Saved to {filename}")
    return filename

def transcribe(filename, model_size="small"):
    model = get_model(model_size)
    segments, info = model.transcribe(filename, beam_size=5, word_timestamps=True)
    seg_list = []
    all_words = []
    full_text_parts = []
    for seg in segments:
        words = []
        for w in seg.words:
            word_dict = {
                "word": w.word,
                "start": w.start,
                "end": w.end,
                "prob": w.probability
            }
            words.append(word_dict)
            all_words.append(word_dict)
        seg_list.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "words": words
        })
        full_text_parts.append(seg.text)
    transcript = " ".join(full_text_parts).strip()
    return transcript, seg_list, all_words

def compute_speech_rate(all_words):
    if not all_words:
        return {"num_words": 0, "duration_sec": 0,
                "words_per_min_total": 0, "words_per_min_speaking_only": 0}
    duration_total = all_words[-1]["end"] - all_words[0]["start"]
    speaking_time = sum(w["end"] - w["start"] for w in all_words)
    num_words = len(all_words)
    return {
        "num_words": num_words,
        "duration_sec": round(duration_total, 2),
        "words_per_min_total": round(num_words / (duration_total / 60), 2) if duration_total > 0 else 0,
        "words_per_min_speaking_only": round(num_words / (speaking_time / 60), 2) if speaking_time > 0 else 0
    }

def compute_pauses(all_words, pause_threshold=0.5):
    pauses = []
    for prev, cur in zip(all_words, all_words[1:]):
        gap = cur["start"] - prev["end"]
        if gap > pause_threshold:
            pauses.append({
                "after_word": prev["word"],
                "duration": round(gap, 2)
            })
    avg = round(sum(p["duration"] for p in pauses) / len(pauses), 2) if pauses else 0
    return {
        "pause_count": len(pauses),
        "avg_pause_sec": avg,
        "max_pause_sec": max((p["duration"] for p in pauses), default=0),
        "pauses": pauses
    }

def compute_filler_words(transcript):
    filler_types = ["um", "uh", "like", "you know",
                    "sort of", "kind of", "i mean", "ah", "erm"]
    breakdown = {}
    for f in filler_types:
        count = len(re.findall(rf"\b{re.escape(f)}\b", transcript, re.IGNORECASE))
        breakdown[f] = count
    return {
        "filler_total": sum(breakdown.values()),
        "filler_breakdown": breakdown
    }

def find_low_confidence_words(all_words, threshold=0.60):
    low = [w for w in all_words if w["prob"] < threshold and w["word"].strip()]
    return {"count": len(low), "words": low}

def merge_low_confidence_phrases(low_words, max_gap=0.25):
    if not low_words:
        return []
    low_words = sorted(low_words, key=lambda x: x["start"])
    phrases = []
    current = [low_words[0]]
    for w in low_words[1:]:
        if w["start"] - current[-1]["end"] <= max_gap:
            current.append(w)
        else:
            phrases.append(current)
            current = [w]
    phrases.append(current)
    merged = []
    for phrase in phrases:
        merged.append({
            "text": " ".join(w["word"] for w in phrase),
            "start": phrase[0]["start"],
            "end": phrase[-1]["end"],
            "avg_prob": round(sum(w["prob"] for w in phrase) / len(phrase), 3)
        })
    return merged

def detect_repetitions(all_words):
    reps = []
    for i in range(len(all_words) - 1):
        w1 = all_words[i]["word"].strip().lower()
        w2 = all_words[i + 1]["word"].strip().lower()
        if w1 and w1 == w2:
            reps.append({
                "word": w1,
                "start": all_words[i]["start"],
                "end": all_words[i + 1]["end"]
            })
    return {"repetition_count": len(reps), "repetitions": reps}

def analyze(transcript, all_words):
    low_conf = find_low_confidence_words(all_words)
    return {
        "speech_rate": compute_speech_rate(all_words),
        "pause_stats": compute_pauses(all_words),
        "filler_stats": compute_filler_words(transcript),
        "low_confidence": {
            "word_count": low_conf["count"],
            "phrases": merge_low_confidence_phrases(low_conf["words"])
        },
        "repetition_stats": detect_repetitions(all_words)
    }

def save_output(transcript, segments, analysis, turn=1):
    output_path = f"recordings/transcript_turn{turn}.json"
    output = {
        "transcript": transcript,
        "segments": segments,
        "analysis": analysis
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    return output, output_path

if __name__ == "__main__":
    turn = 1
    if os.path.exists("recordings/feedback.json"):
        with open("recordings/feedback.json", "r") as f:
            history = json.load(f)
        if history:
            turn = history[-1]["turn"] + 1

    print(f"Recording for Turn {turn}")
    audio_file = record_audio(turn=turn)
    transcript, segments, all_words = transcribe(audio_file)
    analysis = analyze(transcript, all_words)
    output, output_path = save_output(transcript, segments, analysis, turn=turn)

    print("\n--- Transcript ---")
    print(output["transcript"])

    print("\n--- Segments ---")
    for seg in output["segments"]:
        print(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")

    print("\n--- Analysis ---")
    print(f"WPM (speaking): {analysis['speech_rate']['words_per_min_speaking_only']}")
    print(f"Pauses: {analysis['pause_stats']['pause_count']}")
    print(f"Fillers: {analysis['filler_stats']['filler_total']}")
    print(f"Low confidence words: {analysis['low_confidence']['word_count']}")
    print(f"Repetitions: {analysis['repetition_stats']['repetition_count']}")
    print(f"\nSaved to {output_path}")