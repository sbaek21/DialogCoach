import ollama
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coach.scenarios import resolve_scenario, preset_choices

SYSTEM_PROMPT = """
You are DialogCoach, an expert conversational coach helping users improve their spoken dialogue.

You will receive a transcript, a conversation context, and delivery analysis features.
Provide structured feedback in exactly these 4 sections:

1. DELIVERY: Use the provided analysis features (WPM, fillers, pauses, repetitions,
   low confidence words) to give specific, data-driven observations.
2. LINGUISTIC QUALITY: Evaluate vocabulary, sentence structure, grammar, and clarity.
3. COMMUNICATION EFFECTIVENESS: Assess whether tone and content fits the context.
   Is it appropriate, confident, and engaging?
4. IMPROVEMENT SUGGESTIONS: Rewrite 1-2 key sentences to be stronger and explain why.

Be specific, actionable, and encouraging.
Reference exact phrases from the transcript when giving feedback.
"""

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
    analysis_str = json.dumps(analysis, indent=2)
    message = f"""
Context: {context}
Turn {turn} transcript: {transcript}

Delivery analysis:
{analysis_str}
"""
    if history and turn > 1:
        message += f"""
Previous turn feedback:
{history}

Please evaluate the current transcript, reference the delivery analysis features,
and compare to the previous attempt. Note what improved and what still needs work.
"""
    else:
        message += "\nPlease provide structured coaching feedback."
    return message

def get_feedback(transcript, context, analysis, history=None, turn=1):
    user_message = build_user_message(transcript, context, analysis, turn, history)
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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