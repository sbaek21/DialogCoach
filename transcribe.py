"""Local transcription: audio file → console + transcription.txt (faster-whisper).

Colab browser recording lives in transcribe_colab.py.

Requires:
  - Python deps: pip install -r requirements.txt
  - ffmpeg on PATH (macOS: brew install ffmpeg)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def _run_ffmpeg_to_wav(src: Path, dst_wav: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(dst_wav),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            "ffmpeg not found. Install it (e.g. macOS: brew install ffmpeg) and retry."
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or str(e)) from e


def prepare_wav(audio_path: Path) -> Path:
    if audio_path.suffix.lower() == ".wav":
        return audio_path
    out = audio_path.with_name(audio_path.stem + "_16k_mono.wav")
    _run_ffmpeg_to_wav(audio_path, out)
    return out


def default_compute_type(device: str) -> str:
    if device == "cuda":
        return "float16"
    return "int8"


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe a local audio file with faster-whisper.")
    parser.add_argument("audio", type=Path, help="Path to audio (wav, mp3, m4a, webm, …).")
    parser.add_argument(
        "--model",
        default="small",
        help='Model size, e.g. "tiny", "small", "medium", "large-v3" (larger = slower on CPU).',
    )
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument(
        "--compute-type",
        default=None,
        help='Override compute type (default: int8 on cpu, float16 on cuda), e.g. "float32".',
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("transcription.txt"),
        help="Where to write the full transcript text.",
    )
    args = parser.parse_args()

    if not args.audio.is_file():
        print(f"File not found: {args.audio}", file=sys.stderr)
        return 1
    if shutil.which("ffmpeg") is None:
        print("ffmpeg is not on PATH. Install ffmpeg and retry.", file=sys.stderr)
        return 1

    wav_path = prepare_wav(args.audio)
    compute_type = args.compute_type or default_compute_type(args.device)

    model = WhisperModel(args.model, device=args.device, compute_type=compute_type)
    segments, info = model.transcribe(str(wav_path), beam_size=3, temperature=0.3)

    print(
        "Detected language '%s' with probability %f"
        % (info.language, info.language_probability)
    )

    parts: list[str] = []
    for seg in segments:
        print("[%.2fs -> %.2fs] %s" % (seg.start, seg.end, seg.text))
        parts.append(seg.text)

    final_text = " ".join(parts).strip()
    print("\nFinal transcription:\n", final_text, sep="")

    args.output.write_text(final_text, encoding="utf-8")
    print(f"\nSaved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
