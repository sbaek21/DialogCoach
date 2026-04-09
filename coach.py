"""LLM coaching via OpenRouter with optional chain-of-thought reasoning (multi-turn)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI


def _env_streaming_default() -> bool:
    return os.environ.get("OPENROUTER_STREAM", "1").lower() not in ("0", "false", "no")


def _stream_completion(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict[str, Any]],
    extra_body: dict[str, Any] | None,
    section_title: str,
) -> tuple[str, Any]:
    """Stream assistant tokens to stdout; return (full_text, reasoning_details_or_none)."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body

    stream = client.chat.completions.create(**kwargs)
    parts: list[str] = []
    reasoning_details: Any = None

    print(f"\n{section_title}", flush=True)
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        piece = getattr(delta, "content", None) or ""
        if piece:
            parts.append(piece)
            print(piece, end="", flush=True)
        rd = getattr(delta, "reasoning_details", None)
        if rd is not None:
            reasoning_details = rd
    print(flush=True)
    return ("".join(parts), reasoning_details)

FILLERS_FROM_TEXT = re.compile(r"\b(um+|uh+|like|you know)\b", re.IGNORECASE)

DEFAULT_MODEL = "minimax/minimax-m2.5:free"

JUDGE_SYSTEM = """
You are an expert dialogue coach evaluator. Your task in THIS turn is to JUDGE only.

Score the user's spoken answer (from transcript) on these dimensions (1–5 each, 5 best). Be specific and cite the transcript briefly.
1. Delivery: pacing, fillers, clarity of articulation (infer from disfluencies and length).
2. Linguistic quality: clarity, structure, vocabulary.
3. Communication effectiveness: fit to the scenario, concreteness, whether goals/next steps are clear.

Output in this exact structure:
## Rubric scores
- Delivery: <1-5> — <one line>
- Linguistic quality: <1-5> — <one line>
- Communication effectiveness: <1-5> — <one line>
## Top strengths
- ...
## Top gaps
- ...
"""

IMPROVE_USER = """Based on your judgment above, now produce IMPROVEMENT coaching for the learner.

Use these four sections (match the DialogCoach levels):
### Level 1 – Delivery
Concrete observations tied to the provided delivery features when relevant.

### Level 2 – Linguistic Quality
What to change in wording, structure, or specificity.

### Level 3 – Communication Effectiveness
How to better match the scenario and audience intent.

### Level 4 – Improvement Suggestions
Give a short rewritten example answer the user could say next time, plus 2–3 concrete practice steps.

Keep the tone supportive and actionable."""


def _openrouter_client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "Set OPENROUTER_API_KEY in the environment (export OPENROUTER_API_KEY=...)."
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
    )


def _assistant_message_dict(msg: Any) -> dict[str, Any]:
    """Build a message dict for the next request; preserve reasoning_details if present."""
    out: dict[str, Any] = {
        "role": "assistant",
        "content": msg.content or "",
    }
    details = getattr(msg, "reasoning_details", None)
    if details is not None:
        out["reasoning_details"] = details
    return out


def _user_payload(scenario: str, transcript: str, features: dict) -> str:
    return (
        f"## Scenario\n{scenario}\n\n"
        f"## Transcript\n{transcript}\n\n"
        f"## Delivery features\n```json\n{json.dumps(features, ensure_ascii=False, indent=2)}\n```\n"
    )


def infer_features_from_transcript_text(transcript: str) -> dict[str, Any]:
    """When only a text file exists: approximate fillers; timing-based fields are unknown."""
    return {
        "wpm": None,
        "filler_count": len(FILLERS_FROM_TEXT.findall(transcript)),
        "long_pauses": None,
        "note": "Transcript-only: no audio timestamps; infer pacing/pauses from text when needed.",
    }


def judge_and_improve_from_transcript_file(
    transcript_path: str | Path,
    scenario: str,
    *,
    encoding: str = "utf-8",
    stream: bool | None = None,
) -> str:
    """Read a transcript file (e.g. transcribe.txt) and run the same two-turn judge → improve flow."""
    path = Path(transcript_path)
    transcript = path.read_text(encoding=encoding).strip()
    if not transcript:
        raise ValueError(f"Transcript file is empty: {path}")
    features = infer_features_from_transcript_text(transcript)
    text, _ = get_feedback(scenario, transcript, features, stream=stream)
    return text


def get_feedback(
    scenario: str,
    transcript: str,
    features: dict,
    *,
    stream: bool | None = None,
) -> tuple[str, bool]:
    """Two-turn OpenRouter: judge then improvement.

    Returns (formatted_feedback, streamed_to_stdout). If streamed_to_stdout is True, the
    caller may skip re-printing the same text. Use stream=False to disable; None = env OPENROUTER_STREAM.
    """
    client = _openrouter_client()
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    extra = {"reasoning": {"enabled": True}}

    do_stream = _env_streaming_default() if stream is None else stream

    print(f"  OpenRouter model: {model}  (streaming: {do_stream})", flush=True)

    user_content = _user_payload(scenario, transcript, features)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    if do_stream:
        print(f"\n--- Model ---\n{model}\n", flush=True)
        print("  (1/2) Judge (streaming)…", flush=True)
        judge_raw, rd1 = _stream_completion(
            client,
            model=model,
            messages=messages,
            extra_body=extra,
            section_title="--- Judge (turn 1) ---",
        )
        judge_block = judge_raw.strip()
        asst: dict[str, Any] = {"role": "assistant", "content": judge_block}
        if rd1 is not None:
            asst["reasoning_details"] = rd1
        messages.append(asst)
        messages.append({"role": "user", "content": IMPROVE_USER})

        print("  (2/2) Improvement (streaming)…", flush=True)
        improve_raw, _ = _stream_completion(
            client,
            model=model,
            messages=messages,
            extra_body=extra,
            section_title="--- Improvement (turn 2) ---",
        )
        improve_block = improve_raw.strip()
    else:
        print("  (1/2) Waiting for judge response…", flush=True)
        r1 = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=extra,
        )
        m1 = r1.choices[0].message
        messages.append(_assistant_message_dict(m1))
        messages.append({"role": "user", "content": IMPROVE_USER})

        print("  (2/2) Waiting for improvement response…", flush=True)
        r2 = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=extra,
        )
        m2 = r2.choices[0].message
        judge_block = (m1.content or "").strip()
        improve_block = (m2.content or "").strip()

    out = (
        f"--- Model ---\n{model}\n\n"
        f"--- Judge (turn 1) ---\n{judge_block}\n\n"
        f"--- Improvement (turn 2) ---\n{improve_block}\n"
    )
    return (out, do_stream)
