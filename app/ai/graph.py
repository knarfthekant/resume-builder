from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.ai.types import SelectionSuggestion
from app.models import BulletLibrary, ResumeProfile


class SuggestionState(TypedDict, total=False):
    job_description: str
    feedback: str
    previous_suggestion: str
    suggestion: SelectionSuggestion


def build_prompt(
    profile: ResumeProfile,
    library: BulletLibrary,
    job_description: str,
    feedback: str = "",
    previous_suggestion: str = "",
) -> str:
    summary_lines = [_format_option_line(option) for option in library.summary_options]
    experience_lines = []
    for entry in profile.experience_entries:
        experience_lines.append(
            f"Experience {entry.id} ({entry.title} at {entry.company}, min {entry.min_bullets}, max {entry.max_bullets} bullets):"
        )
        for option in library.experience.get(entry.id, []):
            experience_lines.append(f"  {_format_option_line(option)}")

    project_lines = []
    for entry in profile.project_entries:
        project_lines.append(
            f"Project {entry.id} ({entry.name}, min {entry.min_bullets}, max {entry.max_bullets} bullets):"
        )
        for option in library.projects.get(entry.id, []):
            project_lines.append(f"  {_format_option_line(option)}")

    return (
        "You are selecting resume content for a job application.\n"
        "Choose bullet IDs from the provided inventory, keep claims truthful, and only rewrite bullets when it materially helps alignment.\n"
        "Do not invent companies, impact, or technologies.\n\n"
        f"Select between {profile.min_experience_entries} and {profile.max_experience_entries} experience entries.\n"
        f"Select between {profile.min_project_entries} and {profile.max_project_entries} project entries.\n\n"
        f"Job description:\n{job_description}\n\n"
        f"User feedback to incorporate:\n{feedback or '(none)'}\n\n"
        f"Previous suggestion:\n{previous_suggestion or '(none)'}\n\n"
        f"Summary options:\n{chr(10).join(summary_lines) or '(none)'}\n\n"
        f"{chr(10).join(experience_lines)}\n\n"
        f"{chr(10).join(project_lines)}\n"
    )


def _format_option_line(option) -> str:
    parts = [f"- {option.id}: {option.text}"]
    if option.tags:
        parts.append(f"tags={', '.join(option.tags)}")
    return " | ".join(parts)


def build_selection_graph(model, profile: ResumeProfile, library: BulletLibrary):
    structured_model = model.with_structured_output(SelectionSuggestion)

    def suggest_node(state: SuggestionState) -> SuggestionState:
        prompt = build_prompt(
            profile=profile,
            library=library,
            job_description=state["job_description"],
            feedback=state.get("feedback", ""),
            previous_suggestion=state.get("previous_suggestion", ""),
        )
        suggestion = structured_model.invoke(prompt)
        return {"suggestion": suggestion}

    graph = StateGraph(SuggestionState)
    graph.add_node("suggest", suggest_node)
    graph.add_edge(START, "suggest")
    graph.add_edge("suggest", END)
    return graph.compile()
