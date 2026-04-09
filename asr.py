from faster_whisper import WhisperModel
import re


FILLERS = re.compile(r"\b(um+|uh+|like|you know)\b", re.IGNORECASE)


def _load_model():
    """Load the Whisper model once and reuse it."""
    # You can switch between "tiny", "base", "small", "medium", "large"
    # and adjust compute_type depending on your hardware.
    return WhisperModel("small", device="cpu", compute_type="int8")


_MODEL = None


def get_model():
    """Lazy-load global model instance."""
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()
    return _MODEL


def transcribe(audio_path: str):
    """Transcribe an audio file and return transcript and segments.

    Args:
        audio_path: Path to an audio file (e.g., WAV/MP3).

    Returns:
        transcript: Full transcript string.
        segments: List of dicts with keys {start, end, text}.
    """
    model = get_model()
    segments, info = model.transcribe(audio_path, beam_size=5)

    seg_list = []
    full_text_parts = []

    for seg in segments:
        seg_list.append({"start": seg.start, "end": seg.end, "text": seg.text})
        full_text_parts.append(seg.text)

    transcript = " ".join(full_text_parts).strip()
    return transcript, seg_list


def extract_delivery_features(transcript: str, segments):
    """Compute simple delivery-related features from transcript and segments.

    Returns a dict with words-per-minute, filler count, and number of long pauses.
    """
    if not segments:
        return {"wpm": 0.0, "filler_count": 0, "long_pauses": 0}

    words = transcript.split()
    duration = segments[-1]["end"] - segments[0]["start"]
    wpm = len(words) / (duration / 60.0) if duration > 0 else 0.0

    filler_count = len(FILLERS.findall(transcript))

    long_pauses = 0
    for prev, cur in zip(segments, segments[1:]):
        gap = cur["start"] - prev["end"]
        if gap > 0.8:
            long_pauses += 1

    return {"wpm": wpm, "filler_count": filler_count, "long_pauses": long_pauses}
