import argparse
import sys
from pathlib import Path

from asr import transcribe, extract_delivery_features
from coach import get_feedback, infer_features_from_transcript_text
from scenarios import DEFAULT_PRESET, SCENARIOS, preset_choices, resolve_scenario


def _print_and_save_feedback(
    feedback: str, out_path: Path, *, already_streamed: bool
) -> None:
    if already_streamed:
        print("\n=== Feedback (streamed above; same text saved to file) ===", flush=True)
    else:
        print("\n=== Feedback ===")
        print(feedback)
    out_path = out_path.expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(feedback, encoding="utf-8")
    print(f"\nSaved feedback to {out_path.resolve()}", flush=True)


def run_pipeline(
    audio_path: str,
    scenario: str,
    scenario_label: str,
    feedback_out: Path,
    *,
    stream: bool | None,
):
    print("Transcribing audio...")
    transcript, segments = transcribe(audio_path)
    print("\n=== Transcript ===")
    print(transcript)

    print("\nExtracting delivery features...")
    features = extract_delivery_features(transcript, segments)
    print("\n=== Delivery Features ===")
    for k, v in features.items():
        print(f"{k}: {v}")

    print(f"\n=== Coaching scenario ({scenario_label}) ===")
    print(scenario)
    print("\nGenerating coaching feedback...")
    feedback, streamed = get_feedback(scenario, transcript, features, stream=stream)
    _print_and_save_feedback(feedback, feedback_out, already_streamed=streamed)


def run_from_transcript_file(
    transcript_path: Path,
    scenario: str,
    scenario_label: str,
    feedback_out: Path,
    *,
    stream: bool | None,
):
    transcript = transcript_path.read_text(encoding="utf-8").strip()
    if not transcript:
        print(f"Error: transcript file is empty: {transcript_path}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Loaded transcript from {transcript_path}")
    print("\n=== Transcript ===")
    print(transcript)

    features = infer_features_from_transcript_text(transcript)
    print("\n=== Delivery features (transcript-only) ===")
    for k, v in features.items():
        print(f"{k}: {v}")

    print(f"\n=== Coaching scenario ({scenario_label}) ===")
    print(scenario)
    print("\nGenerating coaching feedback (judge → improvement)...")
    feedback, streamed = get_feedback(scenario, transcript, features, stream=stream)
    _print_and_save_feedback(feedback, feedback_out, already_streamed=streamed)


def _print_scenario_list() -> None:
    print("Preset scenarios (--preset <id>):")
    for key in preset_choices():
        blurb = SCENARIOS[key].replace("\n", " ")
        if len(blurb) > 100:
            blurb = blurb[:97] + "..."
        print(f"  {key:22}  {blurb}")
    print(f"\nDefault preset: {DEFAULT_PRESET}")
    print("Override with free text: --custom-scenario \"...\"")


def main():
    parser = argparse.ArgumentParser(description="DialogCoach Whisper + coaching pipeline (single turn).")
    parser.add_argument(
        "audio_path",
        nargs="?",
        default=None,
        help="Path to an audio file (e.g., WAV/MP3). Omit if using --transcript.",
    )
    parser.add_argument(
        "--transcript",
        "-t",
        type=Path,
        default=None,
        help="Path to a transcript text file (e.g. transcribe.txt). Skips ASR; runs judge + improvement only.",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=preset_choices(),
        metavar="ID",
        help=f"Which preset scenario to use (default: {DEFAULT_PRESET}). See --list-scenarios.",
    )
    parser.add_argument(
        "--custom-scenario",
        "-S",
        default=None,
        metavar="TEXT",
        help="Custom scenario description; overrides --preset when set.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print available preset ids and exit.",
    )
    parser.add_argument(
        "--feedback-out",
        type=Path,
        default=Path("feedback.txt"),
        metavar="PATH",
        help="Where to save LLM feedback (default: feedback.txt in the current directory).",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable token streaming; wait for full responses (see also OPENROUTER_STREAM=0).",
    )
    args = parser.parse_args()

    if args.list_scenarios:
        _print_scenario_list()
        raise SystemExit(0)

    scenario_label, scenario_text = resolve_scenario(args.preset, args.custom_scenario)
    stream_flag: bool | None = False if args.no_stream else None

    if args.transcript is not None:
        if not args.transcript.is_file():
            parser.error(f"Transcript file not found: {args.transcript}")
        run_from_transcript_file(
            args.transcript,
            scenario_text,
            scenario_label,
            args.feedback_out,
            stream=stream_flag,
        )
    elif args.audio_path:
        run_pipeline(
            args.audio_path,
            scenario_text,
            scenario_label,
            args.feedback_out,
            stream=stream_flag,
        )
    else:
        parser.error("Provide an audio file path or --transcript /path/to/transcribe.txt")


if __name__ == "__main__":
    main()

