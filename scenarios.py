"""Preset conversation scenarios for coaching (edit or extend this dict)."""

from __future__ import annotations

# id -> full description passed to the LLM as "scenario"
SCENARIOS: dict[str, str] = {
    "coffee_chat": (
        "College student preparing for a casual coffee chat with an alum or mentor. "
        "Goals: build rapport, show genuine interest, ask thoughtful questions, "
        "and leave a clear impression without sounding rehearsed."
    ),
    "research_pitch": (
        "Graduate or advanced undergraduate introducing their research to a professor "
        "or lab PI in ~2 minutes. Goals: problem, approach, one result, and why it fits their group."
    ),
    "elevator_pitch": (
        "Short (~30–60s) elevator pitch about yourself or a project to a recruiter or investor. "
        "Goals: hook, credibility, concrete outcome, and a clear ask."
    ),
    "team_intro": (
        "New teammate introducing themselves on the first day of an internship or class project. "
        "Goals: relevant background, what you want to learn, and how you like to collaborate."
    ),
    "interview_behavioral": (
        "Behavioral interview answer (e.g., conflict, failure, leadership). "
        "Goals: clear situation/task/action/result, specifics not clichés, and honest reflection."
    ),
    "career_fair": (
        "Quick booth conversation at a career fair with a company representative. "
        "Goals: who you are, what you want, one concrete question, and a polite close."
    ),
}

DEFAULT_PRESET = "coffee_chat"


def resolve_scenario(preset: str, custom: str | None) -> tuple[str, str]:
    """Return (label_for_display, scenario_text_for_llm).

    If custom is non-empty, use it and label 'custom'. Otherwise use SCENARIOS[preset].
    """
    if custom and custom.strip():
        return ("custom", custom.strip())
    if preset not in SCENARIOS:
        raise KeyError(f"Unknown preset {preset!r}. Known: {', '.join(sorted(SCENARIOS))}")
    return (preset, SCENARIOS[preset])


def preset_choices() -> list[str]:
    return sorted(SCENARIOS.keys())
