## DialogCoach System Pipelines

This document describes the main pipelines for the **DialogCoach: A Context-Aware LLM Agent for Iterative Spoken Dialogue Improvement** project.

---

## 1. Core Coaching Pipeline (Single Turn)

1. **Scenario Selection**
  - User selects a conversational setting (e.g., coffee chat, elevator pitch, research pitch, team introduction).
  - System records scenario metadata (role, audience, goal).
2. **Speech Capture**
  - UI records audio from the user (microphone input).
  - Audio is stored temporarily (e.g., WAV/MP3) for processing and logging.
3. **Speech-to-Text (ASR)**
  - Audio is passed to an ASR model (e.g., Whisper).
  - Outputs:
    - Transcript of the utterance.
    - Optional timestamps for words/segments.
4. **Feature Extraction (Delivery Signals)**
  - From ASR output, compute basic features:
    - Speaking rate (words per minute).
    - Filler counts (e.g., "um", "uh", "like", "you know").
    - Long pauses / silences (if timestamps are available).
5. **LLM Coaching Agent**
  - Inputs:
    - Scenario description.
    - Transcript.
    - Delivery features (speaking rate, fillers, pauses).
  - Outputs structured feedback at four levels:
  1. **Delivery**: disfluencies, mumbling hints, pacing, pauses.
  2. **Linguistic Quality**: clarity, sentence structure, vocabulary variety, ambiguity.
  3. **Communication Effectiveness**: fit to scenario, clear goals, concrete examples, follow-up questions.
  4. **Improvement Suggestions**: rewritten example answer, highlighted segments, suggested follow-up questions.
6. **UI Presentation**
  - Feedback is rendered in four collapsible sections (Levels 1–4).
  - Key suggestions and a call to action (e.g., "Try again focusing on X and Y") are highlighted.

---

## 2. N-Turn Coaching Loop

1. **Initialize Session**
  - User chooses scenario and starts a new coaching session.
  - Session ID is created to link all attempts.
2. **Attempt t**
  - Run the **Core Coaching Pipeline** for attempt t.
  - Store:
    - Audio, transcript, features.
    - LLM feedback (Levels 1–4).
3. **Progress-Aware Feedback**
  - For attempts t > 1, the LLM prompt includes:
    - Summary of prior feedback.
    - Previous transcript(s).
  - Agent evaluates:
    - Improvements vs. prior attempts (e.g., fewer fillers, clearer goals).
    - Remaining weaknesses and next-step suggestions.
4. **User Revision**
  - User reviews feedback, optionally reads the example improved response.
  - User records a new attempt focusing on specific aspects (e.g., clearer statement of interests, adding a concrete example).
5. **Stopping Condition**
  - User can stop after a fixed number of attempts or when satisfied.
  - Session summary can be displayed (e.g., trends in filler usage, self-reported confidence).

---

## 3. Evaluation Pipelines

### 3.1 Human-Subject Evaluation

1. **Participant Setup**
  - Recruit students preparing for conversations (career fair, coffee chats, research meetings).
  - Collect consent and brief demographic/background information.
2. **Interaction with DialogCoach**
  - Each participant completes one or more full sessions (multiple attempts per scenario).
  - Log:
    - Raw audio and transcripts.
    - Delivery features (fillers, speaking time, etc.).
    - LLM feedback and iterations.
3. **Pre/Post Measures**
  - Optional pre-questionnaire on confidence and prior preparation habits.
  - Post-session survey and/or short interview:
    - Perceived usefulness of each feedback level.
    - Perceived confidence and preparedness.
    - Trust and satisfaction with the AI coach.
4. **Analysis**
  - Quantitative:
    - Changes in filler-word rate, speaking duration, and lexical variety across attempts.
  - Qualitative:
    - Thematic analysis of open-ended responses about what was helpful or confusing.

### 3.2 LLM-as-a-Judge Evaluation

1. **Rubric Definition**
  - Define explicit criteria for:
    - Delivery quality.
    - Linguistic quality.
    - Contextual effectiveness.
    - Actionability of suggestions.
2. **Judging Pipeline**
  - For a sample of system feedback instances:
    - Provide scenario, transcript, and coach feedback to a stronger reference LLM.
    - Ask it to rate feedback along rubric dimensions (e.g., 1–5 scale with justifications).
3. **Comparison and Diagnostics**
  - Aggregate scores to assess:
    - Consistency and specificity of feedback.
    - Differences across scenarios and user proficiency levels.
  - Use rubric violations and low-scoring examples to refine prompts or pipeline design.

---

## 4. Implementation Notes

- **Frontend**: simple web UI (e.g., Gradio or Streamlit) for audio recording and feedback visualization.
- **Backend**: Python service orchestrating ASR calls, feature extraction, LLM prompting, and logging.
- **Data Storage**: session-based logs (audio paths, transcripts, feedback JSON, survey answers) for analysis and model iteration.

