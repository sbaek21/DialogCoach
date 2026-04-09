import sounddevice as sd
import soundfile as sf
import whisper
import numpy as np
import os
import json

SAMPLE_RATE = 16000

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
        input()  # wait for Enter to stop
    
    audio = np.concatenate(chunks, axis=0)
    sf.write(filename, audio, SAMPLE_RATE)
    print(f"Saved to {filename}")
    return filename

def transcribe(filename, model_size="base"):
    print(f"Loading Whisper '{model_size}' model...")
    model = whisper.load_model(model_size)
    print("Transcribing...")
    result = model.transcribe(filename, word_timestamps=True)
    return result


def save_output(result, turn=1):
    output_path = f"recordings/transcript_turn{turn}.json"
    segments = result["segments"]

    output = {
        "transcript": result["text"],
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "words": [
                    {
                        "word": w["word"],
                        "start": w["start"],
                        "end": w["end"]
                    }
                    for w in seg.get("words", [])
                ]
            }
            for seg in segments
        ]
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return output, output_path

if __name__ == "__main__":
    # Get current turn from feedback history
    turn = 1

    if os.path.exists("recordings/feedback.json"):
        with open("recordings/feedback.json", "r") as f:
            history = json.load(f)
        if history:
            turn = history[-1]["turn"] + 1

    print(f"Recording for Turn {turn}")

    audio_file = record_audio(turn=turn)
    result = transcribe(audio_file)
    output, output_path = save_output(result, turn=turn)

    print("\n--- Transcript ---")
    print(output["transcript"])

    print("\n--- Segments with timing ---")
    for seg in output["segments"]:
        print(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")

    print("\n--- Word-level timestamps ---")
    for seg in output["segments"]:
        for word in seg["words"]:
            print(f"  {word['word']:<15} {word['start']:.2f}s - {word['end']:.2f}s")

    print(f"\nSaved to {output_path}")