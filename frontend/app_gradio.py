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

import sys
import traceback
from collections.abc import Iterator
from datetime import datetime
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
from scenarios import resolve_scenario

# Fixed Whisper size for the UI (matches typical local ASR default).
WHISPER_MODEL_SIZE = "small"

# Labels with emojis (keep in sync with frontend/DialogCoach.jsx SCENARIOS).
_SCENARIO_DROPDOWN_CHOICES: list[tuple[str, str]] = [
    ("☕  Coffee Chat", "coffee_chat"),
    ("🔬  Research Pitch", "research_pitch"),
    ("🛗  Elevator Pitch", "elevator_pitch"),
    ("👋  Team Intro", "team_intro"),
    ("🎯  Behavioral Interview", "interview_behavioral"),
    ("🏢  Career Fair", "career_fair"),
]

_DC_CSS = """
/* --- Hero --- */
.dc-hero {
  padding: 1.75rem 1.5rem 1.5rem;
  margin: -0.5rem -1rem 1.25rem -1rem;
  border-radius: 0 0 18px 18px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(16, 185, 129, 0.1) 50%, rgba(59, 130, 246, 0.08) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top: none;
  box-shadow: 0 12px 40px -12px rgba(15, 23, 42, 0.15);
}
.dc-hero .dc-kicker {
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--body-text-color-subdued, #64748b);
  margin: 0 0 0.35rem 0;
}
.dc-hero h1 {
  margin: 0;
  font-size: 1.85rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  background: linear-gradient(90deg, #4f46e5, #0d9488, #2563eb);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.dc-hero .dc-lead {
  margin: 0.6rem 0 0 0;
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--body-text-color-subdued, #64748b);
  max-width: 36rem;
}

/* --- Columns --- */
.dc-input-column {
  padding: 1rem 1.1rem;
  border-radius: 14px;
  background: var(--background-fill-secondary, rgba(248, 250, 252, 0.85));
  border: 1px solid var(--border-color-primary, #e2e8f0);
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
}
.dc-output-column {
  padding: 0.25rem 0 0 0.5rem;
}

/* --- Cards --- */
.dc-transcript-card {
  border-radius: 12px;
  padding: 0.85rem 1rem 1rem;
  margin-bottom: 1rem;
  background: var(--background-fill-primary, #fff);
  border: 1px solid var(--border-color-primary, #e2e8f0);
  box-shadow: 0 2px 14px rgba(15, 23, 42, 0.06);
}
.dc-panel {
  border-radius: 12px;
  padding: 0.75rem 0.9rem 1rem;
  background: var(--background-fill-primary, #fff);
  border: 1px solid var(--border-color-primary, #e2e8f0);
  box-shadow: 0 2px 14px rgba(15, 23, 42, 0.06);
  height: fit-content;
}
.dc-panel-judge { border-left: 4px solid #4f46e5; }
.dc-panel-improve { border-left: 4px solid #0d9488; }
.dc-panel h3 { margin-top: 0; font-size: 0.95rem; color: var(--body-text-color, #334155); }

/* Judge | Improvement: side-by-side, independent heights (no equal stretch). */
.dc-judge-improve-row {
  display: flex !important;
  flex-direction: row !important;
  align-items: flex-start !important;
  flex-wrap: wrap !important;
  gap: 0.75rem;
}
.dc-judge-improve-row > div {
  flex: 1 1 280px;
  min-width: 0;
}

/* --- Run button accent --- */
.dc-run-wrap button.primary {
  width: 100%;
  font-weight: 600 !important;
  letter-spacing: 0.02em;
  border-radius: 10px !important;
  padding: 0.65rem 1rem !important;
}
"""


def _scenario_text(preset: str, custom: str) -> str:
    custom = (custom or "").strip()
    if custom:
        return resolve_scenario("coffee_chat", custom)[1]
    return resolve_scenario(preset, None)[1]


def run_coaching(
    audio_path: str | None,
    scenario_preset: str,
    custom_scenario: str,
    turn: int,
    history: str | None,
    entries: list[dict] | None,
) -> Iterator[tuple[str, str, str, int, str, list[dict]]]:
    """Yields (transcript, judge_md, improve_md, next_turn, next_history, next_entries).

    We update the UI after transcribe, then judge, then improve. `next_turn` stays
    the same during processing and increments after a successful full run.
    """
    if not audio_path:
        yield ("No audio: record or upload a file.", "", "", turn, history or "", entries or [])
        return
    path = str(audio_path).strip()
    if not path or not Path(path).is_file():
        yield ("Invalid audio file path.", "", "", turn, history or "", entries or [])
        return

    turn = int(turn or 1)
    if turn < 1:
        turn = 1

    history = (history or "").strip() or None
    entries = list(entries or [])
    yield (
        "*Transcribing audio…*",
        "*Waiting for transcript…*",
        "*Waiting for transcript…*",
        turn,
        history or "",
        entries,
    )

    try:
        transcript, _segments, all_words = transcribe(path, model_size=WHISPER_MODEL_SIZE)
    except Exception as e:
        yield (
            f"Transcribe error: {e}\n\n{traceback.format_exc()}",
            "",
            "",
            turn,
            history or "",
            entries,
        )
        return

    if not (transcript or "").strip():
        yield ("Empty transcript (no speech detected?).", "", "", turn, history or "", entries)
        return

    # Show transcript as soon as ASR finishes; judge/improve still pending.
    yield (
        transcript,
        "*Running judge…*",
        "*Waiting for judge…*",
        turn,
        history or "",
        entries,
    )

    try:
        analysis = analyze(transcript, all_words)
    except Exception as e:
        yield (transcript, f"**Analysis error:** {e}", "", turn, history or "", entries)
        return

    context = _scenario_text(scenario_preset, custom_scenario)
    model = MODEL_NAME

    try:
        judge = judge_evaluation(
            transcript, context, analysis, turn=turn, model=model
        )
    except Exception as e:
        yield (
            transcript,
            f"**Judge error:** {e}\n\n```\n{traceback.format_exc()}\n```",
            "",
            turn,
            history or "",
            entries,
        )
        return

    yield (
        transcript,
        judge,
        "*Running improvement…*",
        turn,
        history or "",
        entries,
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
            history=history,
        )
    except Exception as e:
        yield (
            transcript,
            judge,
            f"**Improvement error:** {e}\n\n```\n{traceback.format_exc()}\n```",
            turn,
            history or "",
            entries,
        )
        return

    next_history = f"{judge}\n\n---\n\n{improve}"
    scenario_label = next((lbl for (lbl, sid) in _SCENARIO_DROPDOWN_CHOICES if sid == scenario_preset), scenario_preset)
    entry = {
        "turn": turn,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "scenario_id": scenario_preset,
        "scenario_label": scenario_label,
        "transcript": transcript,
        "judge": judge,
        "improvement": improve,
    }
    # IMPORTANT: return a new list object so Gradio State change is detected.
    next_entries = [*entries, entry]
    yield (transcript, judge, improve, turn + 1, next_history, next_entries)


def build_app() -> gr.Blocks:
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.indigo,
        secondary_hue=gr.themes.colors.teal,
        neutral_hue=gr.themes.colors.slate,
        radius_size=gr.themes.sizes.radius_lg,
        spacing_size=gr.themes.sizes.spacing_md,
    )

    with gr.Blocks(
        title="DialogCoach",
        theme=theme,
        css=_DC_CSS,
    ) as app:
        gr.HTML(
            """
<div class="dc-hero">
  <p class="dc-kicker">User-centered speaking coach</p>
  <h1>DialogCoach</h1>
  <p class="dc-lead">
    Record or upload audio → local Whisper transcription →
    <strong>Judge</strong> then <strong>Improve</strong>.
  </p>
</div>
            """.strip()
        )

        turn_state = gr.State(1)
        prior_feedback_state = gr.State("")
        history_entries_state = gr.State([])  # list of dicts

        with gr.Tabs():
            with gr.Tab("Coach"):
                with gr.Row():
                    with gr.Column(scale=5, elem_classes=["dc-input-column"]):
                        turn_badge = gr.Markdown("**Turn:** 1")
                        scenario = gr.Dropdown(
                            choices=_SCENARIO_DROPDOWN_CHOICES,
                            value="coffee_chat",
                            label="Scenario",
                        )
                        with gr.Accordion("Custom scenario (optional)", open=False):
                            custom = gr.Textbox(
                                show_label=False,
                                lines=3,
                                placeholder="Overrides the dropdown when non-empty. E.g. “Practice a 60s research pitch to a non-expert.”",
                            )
                        audio = gr.Audio(
                            type="filepath",
                            sources=["microphone", "upload"],
                            label="Audio",
                        )
                        with gr.Row(elem_classes=["dc-run-wrap"]):
                            run_btn = gr.Button(
                                "Transcribe & get coaching",
                                variant="primary",
                                scale=1,
                            )
                        rerecord_btn = gr.Button("New Recording (clear audio)", variant="secondary")
                        reset_btn = gr.Button("Start New Coaching (keep history)", variant="secondary")

                    with gr.Column(scale=7, elem_classes=["dc-output-column"]):
                        with gr.Column(elem_classes=["dc-transcript-card"]):
                            gr.Markdown("#### Transcript")
                            out_tr = gr.Textbox(
                                show_label=False,
                                lines=5,
                                max_lines=12,
                                placeholder="Transcribed text will appear here…",
                            )

                        with gr.Row(equal_height=False, elem_classes=["dc-judge-improve-row"]):
                            with gr.Column(scale=1, elem_classes=["dc-panel", "dc-panel-judge"]):
                                gr.Markdown("#### Judge")
                                out_ju = gr.Markdown(
                                    value="*Evaluation will appear after you run.*",
                                )
                            with gr.Column(scale=1, elem_classes=["dc-panel", "dc-panel-improve"]):
                                gr.Markdown("#### Improvement")
                                out_im = gr.Markdown(
                                    value="*Coaching will appear after you run.*",
                                )

            with gr.Tab("History"):
                gr.Markdown("#### Past Coaching Sessions")
                hist_meta = gr.Markdown("*No Coaching Sessions yet.*")
                with gr.Row(equal_height=False):
                    with gr.Column(scale=2):
                        history_select = gr.Dropdown(
                            choices=[],
                            value=None,
                            label="Select a Coaching Session",
                        )
                    with gr.Column(scale=3):
                        hist_transcript = gr.Textbox(label="Transcript", lines=4)
                with gr.Row(equal_height=False, elem_classes=["dc-judge-improve-row"]):
                    with gr.Column(scale=1, elem_classes=["dc-panel", "dc-panel-judge"]):
                        gr.Markdown("#### Judge")
                        hist_judge = gr.Markdown()
                    with gr.Column(scale=1, elem_classes=["dc-panel", "dc-panel-improve"]):
                        gr.Markdown("#### Improvement")
                        hist_improve = gr.Markdown()

        run_btn.click(
            run_coaching,
            inputs=[audio, scenario, custom, turn_state, prior_feedback_state, history_entries_state],
            outputs=[out_tr, out_ju, out_im, turn_state, prior_feedback_state, history_entries_state],
        )

        def _show_turn(t: int) -> str:
            t = int(t or 1)
            if t < 1:
                t = 1
            return f"**Turn:** {t}"

        turn_state.change(_show_turn, inputs=[turn_state], outputs=[turn_badge])

        # Start a new coaching session (turn resets), but keep history for review.
        reset_btn.click(lambda: (1, ""), inputs=None, outputs=[turn_state, prior_feedback_state])

        # Clear audio input without using the small X button.
        rerecord_btn.click(lambda: None, inputs=None, outputs=[audio])

        def _fmt_ts(ts: str | None) -> str:
            """Format ISO timestamp -> M/D/YYYY H:MM AM/PM."""
            if not ts:
                return ""
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                return str(ts)
            # macOS supports %-m/%-d/%-I (no leading zeros)
            try:
                return dt.strftime("%-m/%-d/%Y %-I:%M %p")
            except Exception:
                # Fallback for platforms without '-' flags
                return dt.strftime("%m/%d/%Y %I:%M %p").lstrip("0").replace("/0", "/")

        def _history_choices(entries: list[dict]):
            opts: list[tuple[str, int]] = []
            for i, e in enumerate(entries or []):
                label = f"Turn {e.get('turn')} · {e.get('scenario_label')} · {_fmt_ts(e.get('timestamp'))}"
                opts.append((label, i))
            # Gradio 6: use gr.update(...) rather than Component.update(...)
            return gr.update(choices=opts, value=(opts[-1][1] if opts else None))

        history_entries_state.change(_history_choices, inputs=[history_entries_state], outputs=[history_select])

        def _view_entry(idx: int | None, entries: list[dict]):
            if idx is None or not entries or idx < 0 or idx >= len(entries):
                return (
                    "*No turns yet.*",
                    "",
                    "",
                    "",
                )
            e = entries[idx]
            meta = f"**Turn {e.get('turn')}** · **{e.get('scenario_label')}** · `{_fmt_ts(e.get('timestamp'))}`"
            return (
                meta,
                e.get("transcript") or "",
                e.get("judge") or "",
                e.get("improvement") or "",
            )

        history_select.change(
            _view_entry,
            inputs=[history_select, history_entries_state],
            outputs=[hist_meta, hist_transcript, hist_judge, hist_improve],
        )
    return app


if __name__ == "__main__":
    build_app().launch()
