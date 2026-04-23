"""
DialogCoach — simple Gradio UI (A path).

From project root:
  pip install -r requirements.txt
  python frontend/app_gradio.py

From this directory:
  python app_gradio.py

Requires: GEMINI_API_KEY in .env at project root (see coach/config.py).
Whisper ASR runs locally (CPU); first run downloads the model.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# Repo root (parent of frontend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from repo root even if cwd is frontend/
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

# coach/* uses `from config` / `from scenarios` (expects coach/ on path)
sys.path.insert(0, str(PROJECT_ROOT / "coach"))
sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr

from asr.transcribe import analyze, transcribe
from config import MODEL_NAME
from feedback_agent_two_stage_api import improvement_coaching, judge_evaluation
from scenarios import preset_choices, resolve_scenario


def _scenario_text(preset: str, custom: str) -> str:
    custom = (custom or "").strip()
    if custom:
        return resolve_scenario("coffee_chat", custom)[1]
    return resolve_scenario(preset, None)[1]


def run_coaching(
    audio_path: str | None,
    scenario_preset: str,
    custom_scenario: str,
    whisper_size: str,
) -> tuple[str, str, str, str, str]:
    if not audio_path:
        return (
            "No audio: record or upload a file.",
            "",
            "",
            "",
            "",
        )
    path = str(audio_path).strip()
    if not path or not Path(path).is_file():
        return ("Invalid audio file path.", "", "", "", "")

    try:
        transcript, _segments, all_words = transcribe(path, model_size=whisper_size)
    except Exception as e:
        return (
            f"Transcribe error: {e}\n\n{traceback.format_exc()}",
            "",
            "",
            "",
            "",
        )

    if not (transcript or "").strip():
        return ("Empty transcript (no speech detected?).", "", "", "", "")

    try:
        analysis = analyze(transcript, all_words)
    except Exception as e:
        return (
            transcript,
            f"Analysis error: {e}",
            "",
            "",
            "",
        )

    context = _scenario_text(scenario_preset, custom_scenario)
    turn = 1
    model = MODEL_NAME

    try:
        judge = judge_evaluation(
            transcript, context, analysis, turn=turn, model=model
        )
    except Exception as e:
        return (
            transcript,
            json.dumps(analysis, indent=2, ensure_ascii=False),
            f"Judge error: {e}\n\n{traceback.format_exc()}",
            "",
            "",
        )

    try:
        improve = improvement_coaching(
            transcript,
            context,
            analysis,
            turn=turn,
            model=model,
            judge_text=judge,
            stream=False,
        )
    except Exception as e:
        return (
            transcript,
            json.dumps(analysis, indent=2, ensure_ascii=False),
            judge,
            f"Improvement error: {e}\n\n{traceback.format_exc()}",
            "",
        )

    analysis_str = json.dumps(analysis, indent=2, ensure_ascii=False)
    combined = (
        "## Judge\n\n"
        f"{judge}\n\n"
        "## Improvement\n\n"
        f"{improve}\n"
    )
    return (transcript, analysis_str, judge, improve, combined)


def build_app() -> gr.Blocks:
    scenario_keys = preset_choices()
    with gr.Blocks(title="DialogCoach") as app:
        gr.Markdown(
            "# DialogCoach\n"
            "Record or upload audio → Whisper transcription → **Judge** + **Improve** (Gemini API)."
        )
        with gr.Row():
            scenario = gr.Dropdown(
                choices=scenario_keys,
                value="coffee_chat",
                label="Scenario",
            )
            whisper = gr.Dropdown(
                choices=["tiny", "base", "small", "medium", "large-v3"],
                value="small",
                label="Whisper model",
            )
        custom = gr.Textbox(
            label="Custom scenario (optional, overrides dropdown if non-empty)",
            lines=2,
            placeholder="e.g. Practice introducing yourself at a club fair...",
        )
        audio = gr.Audio(
            type="filepath",
            sources=["microphone", "upload"],
            label="Audio",
        )
        run_btn = gr.Button("Transcribe & coach", variant="primary")

        out_tr = gr.Textbox(label="Transcript", lines=4)
        out_an = gr.Textbox(label="Delivery features (JSON)", lines=8)
        out_ju = gr.Textbox(label="Judge", lines=12)
        out_im = gr.Textbox(label="Improvement", lines=12)
        out_all = gr.Markdown(label="Combined")

        run_btn.click(
            run_coaching,
            inputs=[audio, scenario, custom, whisper],
            outputs=[out_tr, out_an, out_ju, out_im, out_all],
        )
    return app


if __name__ == "__main__":
    build_app().launch()
