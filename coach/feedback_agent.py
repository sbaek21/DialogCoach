import ollama
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coach.scenarios import resolve_scenario, preset_choices

_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _ROOT / "prompts"


def load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt_single_turn() -> str:
    """Use prompts/ files as the single source of truth (one-turn output)."""
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


def ollama_model() -> str:
    # Override: export OLLAMA_MODEL=... (and make sure it's pulled: `ollama pull ...`)
    return os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

def select_context():
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

def build_user_message(transcript, context, analysis, turn, history=None):
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

def get_feedback(transcript, context, analysis, history=None, turn=1):
    user_message = build_user_message(transcript, context, analysis, turn, history)
    response = ollama.chat(
        model=ollama_model(),
        messages=[
            {"role": "system", "content": build_system_prompt_single_turn()},
            {"role": "user", "content": user_message}
        ]
    )
    return response["message"]["content"]

def save_feedback(feedback, context, transcript, analysis, turn,
                  output_path="recordings/feedback.json"):
    os.makedirs("recordings", exist_ok=True)
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append({
        "turn": turn,
        "timestamp": datetime.now().isoformat(),
        "context": context,
        "transcript": transcript,
        "analysis": analysis,
        "feedback": feedback
    })

    with open(output_path, "w") as f:
        json.dump(history, f, indent=2)
    return history

def load_last_feedback(output_path="recordings/feedback.json"):
    if not os.path.exists(output_path):
        return None, 1
    with open(output_path, "r") as f:
        history = json.load(f)
    if not history:
        return None, 1
    last = history[-1]
    return last["feedback"], last["turn"] + 1

if __name__ == "__main__":
    # Get context from user
    context = select_context()

    # Load previous feedback if exists
    last_feedback, turn = load_last_feedback()

    # Load transcript for current turn
    transcript_path = f"recordings/transcript_turn{turn}.json"
    if not os.path.exists(transcript_path):
        print(f"Error: {transcript_path} not found. Please run transcribe.py first.")
        exit(1)

    with open(transcript_path, "r") as f:
        data = json.load(f)

    transcript = data["transcript"]
    analysis = data.get("analysis", {})

    if last_feedback:
        print(f"\nFound previous session (Turn {turn - 1}). This will be Turn {turn}.")
    else:
        print(f"\nStarting Turn {turn}.")

    print("\nGenerating feedback...\n")
    feedback = get_feedback(transcript, context, analysis,
                            history=last_feedback, turn=turn)

    save_feedback(feedback, context, transcript, analysis, turn)

    print(feedback)
    print(f"\nFeedback saved. (Turn {turn} complete)")