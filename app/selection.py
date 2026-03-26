from __future__ import annotations

from dataclasses import asdict

from app.models import BulletLibrary, BulletOption, ResumeProfile, ResumeSelection


class SelectionValidationError(ValueError):
    pass


class ManualSelectionService:
    def build_default_selection(self, profile: ResumeProfile, library: BulletLibrary) -> ResumeSelection:
        selection = ResumeSelection()
        if library.summary_options:
            selection.summary_id = library.summary_options[0].id

        for entry in profile.experience_entries:
            options = library.experience.get(entry.id, [])
            selection.experience[entry.id] = [option.id for option in options[: entry.max_bullets]]

        for entry in profile.project_entries:
            options = library.projects.get(entry.id, [])
            selection.projects[entry.id] = [option.id for option in options[: entry.max_bullets]]

        self.validate_selection(profile, library, selection)
        return selection

    def validate_selection(
        self,
        profile: ResumeProfile,
        library: BulletLibrary,
        selection: ResumeSelection,
    ) -> ResumeSelection:
        summary_ids = {option.id for option in library.summary_options}
        if selection.summary_id and selection.summary_id not in summary_ids:
            raise SelectionValidationError(f"Unknown summary selection: {selection.summary_id}")

        experience_map = {entry.id: entry for entry in profile.experience_entries}
        project_map = {entry.id: entry for entry in profile.project_entries}

        for entry_id, selected_ids in selection.experience.items():
            if entry_id not in experience_map:
                raise SelectionValidationError(f"Unknown experience entry: {entry_id}")
            if len(set(selected_ids)) != len(selected_ids):
                raise SelectionValidationError(f"Duplicate experience bullets selected for {entry_id}")
            available = {option.id for option in library.experience.get(entry_id, [])}
            invalid = [bullet_id for bullet_id in selected_ids if bullet_id not in available]
            if invalid:
                raise SelectionValidationError(f"Unknown experience bullets for {entry_id}: {', '.join(invalid)}")
            if len(selected_ids) > experience_map[entry_id].max_bullets:
                raise SelectionValidationError(
                    f"Selected too many experience bullets for {entry_id}: "
                    f"{len(selected_ids)} > {experience_map[entry_id].max_bullets}"
                )

        for entry_id, selected_ids in selection.projects.items():
            if entry_id not in project_map:
                raise SelectionValidationError(f"Unknown project entry: {entry_id}")
            if len(set(selected_ids)) != len(selected_ids):
                raise SelectionValidationError(f"Duplicate project bullets selected for {entry_id}")
            available = {option.id for option in library.projects.get(entry_id, [])}
            invalid = [bullet_id for bullet_id in selected_ids if bullet_id not in available]
            if invalid:
                raise SelectionValidationError(f"Unknown project bullets for {entry_id}: {', '.join(invalid)}")
            if len(selected_ids) > project_map[entry_id].max_bullets:
                raise SelectionValidationError(
                    f"Selected too many project bullets for {entry_id}: "
                    f"{len(selected_ids)} > {project_map[entry_id].max_bullets}"
                )

        return selection


class SelectionApplier:
    def build_render_context(
        self,
        profile: ResumeProfile,
        library: BulletLibrary,
        selection: ResumeSelection,
    ) -> dict:
        ManualSelectionService().validate_selection(profile, library, selection)

        summary_text = ""
        if selection.summary_id:
            summary_option = self._find_option(library.summary_options, selection.summary_id)
            summary_text = selection.summary_rewrite or summary_option.text

        experience_sections = []
        for entry in profile.experience_entries:
            selected_ids = selection.experience.get(entry.id, [])
            highlights = self._resolve_texts(library.experience.get(entry.id, []), selected_ids, selection.rewrites)
            if not highlights:
                continue
            experience_sections.append(
                {
                    "title": entry.title,
                    "location": entry.location,
                    "date_range": entry.date_range,
                    "company": entry.company,
                    "highlights": highlights,
                }
            )

        project_sections = []
        for entry in profile.project_entries:
            selected_ids = selection.projects.get(entry.id, [])
            highlights = self._resolve_texts(library.projects.get(entry.id, []), selected_ids, selection.rewrites)
            if not highlights:
                continue
            project_sections.append(
                {
                    "name": entry.name,
                    "tech_stack": entry.tech_stack,
                    "link_url": entry.link_url,
                    "link_label": entry.link_label,
                    "highlights": highlights,
                }
            )

        profile_dict = asdict(profile)
        profile_dict.pop("experience_entries", None)
        profile_dict.pop("project_entries", None)
        profile_dict["highlights"] = {"summary": summary_text}
        profile_dict["experience"] = experience_sections
        profile_dict["projects"] = project_sections
        return profile_dict

    def _resolve_texts(
        self,
        options: list[BulletOption],
        selected_ids: list[str],
        rewrites: dict[str, str],
    ) -> list[str]:
        option_map = {option.id: option for option in options}
        return [rewrites.get(bullet_id) or option_map[bullet_id].text for bullet_id in selected_ids]

    def _find_option(self, options: list[BulletOption], option_id: str) -> BulletOption:
        for option in options:
            if option.id == option_id:
                return option
        raise SelectionValidationError(f"Unknown summary option: {option_id}")
