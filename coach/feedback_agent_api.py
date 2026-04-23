from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from config import MODEL_NAME, GEMINI_API_KEY

from openai import OpenAI

# When running as `python coach/feedback_agent_openrouter.py`, this directory is on sys.path already.
from scenarios import preset_choices, resolve_scenario


def _gemini_client() -> OpenAI:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set (used as GEMINI_API_KEY in config.py)")
    return OpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")


_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _ROOT / "prompts"


def load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt_single_turn() -> str:
    judge = load_prompt("judge_prompt.md")
    improve = load_prompt("improve_prompt.md")
    return (
        f"{judge}\n\n"
        "---\n\n"
        "# Improvement coaching (same reply — after the judge output)\n\n"
        "After you complete the judge section above, continue **in the same response** "
        "with improvement coaching that follows:\n\n"
        f"{improve}\n"
    )


def select_context() -> str:
    choices = preset_choices()
    print("\nSelect your conversation context:")
    for i, key in enumerate(choices, 1):
        print(f"  {i}. {key}")
    choice = input("\nEnter number: ").strip()
    try:
        key = choices[int(choice) - 1]
    except (ValueError, IndexError):
        key = choices[0]
    _, scenario_text = resolve_scenario(key, None)
    return scenario_text


def build_user_message(
    transcript: str,
    context: str,
    analysis: dict[str, Any],
    turn: int,
    history: str | None = None,
) -> str:
    analysis_str = json.dumps(analysis, indent=2, ensure_ascii=False)
    message = f"""## Scenario
{context}

## Transcript (turn {turn})
{transcript}

## Delivery features
```json
{analysis_str}
```
"""
    if history and turn > 1:
        message += (
            "\n## Prior turn feedback (for comparison)\n"
            f"{history}\n\n"
            "Compare this turn to the prior attempt: what improved, what regressed, "
            "and what to focus on next.\n"
        )
    else:
        message += "\nFollow your system prompt output structure.\n"
    return message


def get_feedback(
    transcript: str,
    context: str,
    analysis: dict[str, Any],
    *,
    history: str | None = None,
    turn: int = 1,
    model: str = MODEL_NAME,
    stream: bool = False,
) -> str:
    client = _gemini_client()
    system_prompt = build_system_prompt_single_turn()
    user_message = build_user_message(transcript, context, analysis, turn, history)

    print(f"  Gemini model: {model}", flush=True)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    if not stream:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return (r.choices[0].message.content or "").strip()

    parts: list[str] = []
    s = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    for chunk in s:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        piece = getattr(delta, "content", None) or ""
        if piece:
            parts.append(piece)
            print(piece, end="", flush=True)
    print(flush=True)
    return "".join(parts).strip()


def save_feedback(
    feedback: str,
    context: str,
    transcript: str,
    analysis: dict[str, Any],
    turn: int,
    output_path: str,
) -> list[dict[str, Any]]:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists():
        history = json.loads(out.read_text(encoding="utf-8"))
    else:
        history = []

    history.append(
        {
            "turn": turn,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "transcript": transcript,
            "analysis": analysis,
            "feedback": feedback,
        }
    )
    out.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return history


def load_last_feedback(output_path: str) -> tuple[str | None, int]:
    path = Path(output_path)
    if not path.exists():
        return None, 1
    history = json.loads(path.read_text(encoding="utf-8"))
    if not history:
        return None, 1
    last = history[-1]
    return last.get("feedback"), int(last.get("turn", 0)) + 1


def _load_transcript_json(path: Path) -> tuple[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    transcript = (data.get("transcript") or "").strip()
    if not transcript:
        raise ValueError(f"Missing/empty transcript in: {path}")
    analysis = data.get("analysis") or {}
    if not isinstance(analysis, dict):
        analysis = {}
    return transcript, analysis


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DialogCoach feedback agent (Gemini backend).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model", default=MODEL_NAME, help="Gemini model id (or set MODEL_NAME in config.py)."
    )
    parser.add_argument("--stream", action="store_true", help="Stream tokens while generating.")
    args = parser.parse_args()

    context = select_context()
    last_feedback, turn = load_last_feedback("recordings/feedback.json")
    if turn is None:
        print("No previous session found. Starting new session.")
        turn = 1    
    else:
        print(f"\nFound previous session (Turn {turn - 1}). This will be Turn {turn}.")
    transcript, analysis = _load_transcript_json(Path(f"recordings/transcript_turn{turn}.json"))

    print("\nGenerating feedback...\n", flush=True)
    feedback = get_feedback(
        transcript,
        context,
        analysis,
        history=last_feedback,
        turn=turn,
        model=args.model,
        stream=args.stream,
    )

    save_feedback(
        feedback,
        context,
        transcript,
        analysis,
        turn,
        output_path="recordings/feedback.json",
    )

    if not args.stream:
        print(feedback)
    print(f"\nFeedback saved. (Turn {turn} complete)")
    return 0


if __name__ == "__main__":
    # Get context from user
    context = select_context()

    # Load previous feedback if exists
    last_feedback, turn = load_last_feedback("recordings/feedback.json")

    # Load transcript for current turn          
    transcript, analysis = _load_transcript_json(Path(f"recordings/transcript_turn{turn}.json"))

    if last_feedback:
        print(f"\nFound previous session (Turn {turn - 1}). This will be Turn {turn}.")
    else:
        print(f"\nStarting Turn {turn}.")

    print("\nGenerating feedback...\n")
    feedback = get_feedback(transcript, context, analysis,
                            history=last_feedback, turn=turn)

    save_feedback(feedback, context, transcript, analysis, turn, "recordings/feedback.json")

    print(feedback)
    print(f"\nFeedback saved. (Turn {turn} complete)")

