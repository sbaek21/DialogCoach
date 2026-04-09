import ollama
import json
import os
from datetime import datetime

CONTEXTS = {
    "1": "College student preparing for a casual company coffee chat",
    "2": "College student preparing for a job interview",
    "3": "Student preparing to give an academic or professional presentation",
    "4": "Student preparing for public speaking or a large audience talk"
}

SYSTEM_PROMPT = """
You are DialogCoach, an expert conversational coach helping users improve their spoken dialogue.

Given a transcript and a conversation context, provide structured feedback in exactly these 4 sections:

1. DELIVERY: Identify filler words, hesitation, pacing issues, or unnatural pauses based on the text.
2. LINGUISTIC QUALITY: Evaluate vocabulary, sentence structure, grammar, and clarity.
3. COMMUNICATION EFFECTIVENESS: Assess whether the tone and content fits the given context. Is it appropriate, confident, and engaging?
4. IMPROVEMENT SUGGESTIONS: Rewrite 1-2 key sentences from the transcript to be stronger, and explain why.

Be specific, actionable, and encouraging. Reference exact phrases from the transcript when giving feedback.
"""

def select_context():
    print("\nSelect your conversation context:")
    for key, value in CONTEXTS.items():
        print(f"  {key}. {value}")
    choice = input("\nEnter number (1-4): ").strip()
    return CONTEXTS.get(choice, CONTEXTS["1"])

def get_feedback(transcript, context, history=None, turn=1):
    user_message = f"""
Context: {context}
Current transcript (Turn {turn}): {transcript}
"""
    if history and turn > 1:
        user_message += f"""
Here is the feedback from the previous attempt:
{history}

Please evaluate the current transcript and compare it to the previous attempt. Note what improved and what still needs work.
"""
    else:
        user_message += "\nPlease provide structured coaching feedback."

    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )
    return response["message"]["content"]

def save_feedback(feedback, context, transcript, turn, output_path="recordings/feedback.json"):
    os.makedirs("recordings", exist_ok=True)

    # Load existing feedback history if it exists
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

    if last_feedback:
        print(f"\nFound previous session (Turn {turn - 1}). This will be Turn {turn}.")
    else:
        print(f"\nStarting Turn {turn}.")

    # Generate feedback
    print("\nGenerating feedback...\n")
    feedback = get_feedback(transcript, context, history=last_feedback, turn=turn)

    # Save feedback
    save_feedback(feedback, context, transcript, turn)

    print(feedback)
    print(f"\nFeedback saved. (Turn {turn} complete)")