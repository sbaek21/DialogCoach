# DialogCoach

An interactive AI coaching system for scenario-based spoken communication practice. DialogCoach combines automatic speech recognition, delivery feature extraction, and a two-stage LLM evaluation pipeline to help students improve spoken responses across realistic professional scenarios such as job interviews, coffee chats, elevator pitches, and career fairs.

## Overview

DialogCoach is built around an iterative coaching loop: users record a spoken response, receive structured feedback, and re-record to improve across multiple attempts. Feedback is generated through a two-stage LLM pipeline:

- **Judge** — evaluates the response across three dimensions: Delivery, Linguistic Quality, and Communication Effectiveness using a 1-5 rubric
- **Improvement** — generates personalized coaching, a rewritten model answer, and concrete practice steps based on the Judge's evaluation

## Features

- Microphone recording with press-to-start/stop interface
- Automatic speech recognition via Faster-Whisper
- Delivery feature extraction: words per minute, filler words, pauses, word repetitions
- Scenario-aware LLM evaluation using Gemini 2.5 Flash-Lite
- Multi-turn coaching loop with prior turn comparison
- Six preset communication scenarios plus custom scenario support
- Gradio web interface with Judge and Improvement feedback panels and session history

## Scenarios

- Coffee Chat
- Elevator Pitch
- Behavioral Interview
- Team Introduction
- Research Pitch
- Career Fair

## Tech Stack

- **ASR**: faster-whisper (small model, CPU, int8)
- **LLM**: Gemini 2.5 Flash-Lite via OpenAI-compatible endpoint
- **Frontend**: Gradio
- **Language**: Python 3.12

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/sbaek21/DialogCoach.git
```

### 2. Create and activate conda environment
```bash
conda create -n dialogcoach python=3.12
conda activate dialogcoach
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

GEMINI_API_KEY=your_api_key_here

### 5. Run the application
```bash
python frontend/app_gradio.py
```

Then open the Gradio interface in your browser.

## Project Structure

```
DialogCoach/
├── asr/
│   └── transcribe.py
├── coach/
│   ├── feedback_agent_two_stage_api.py
│   ├── scenarios.py
│   └── config.py
├── prompts/
│   ├── judge_prompt.md
│   └── improve_prompt.md
├── frontend/
│   └── app_gradio.py
├── requirements.txt
└── .env
```

## Authors

Sunwoo Baek, Ju-Bin Choi, Supia Park

---

<!-- Context-aware spoken dialogue coaching: speech-to-text, delivery features, and LLM-based judge → improvement feedback. -->