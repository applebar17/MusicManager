from music_manager_backend.domain.entities import AudioFile, MatchLink


def active_match_links(
    links: list[MatchLink],
    active_files: dict[str, AudioFile],
) -> list[MatchLink]:
    return [link for link in links if link.audio_file_id in active_files]


def preferred_match_link(
    links: list[MatchLink],
    active_files: dict[str, AudioFile],
) -> MatchLink | None:
    active_links = active_match_links(links, active_files)
    manual = [
        link
        for link in active_links
        if link.reviewed and link.method == "manual"
    ]
    if manual:
        return manual[0]
    automatic = [link for link in active_links if not link.reviewed]
    if automatic:
        return automatic[0]
    local_duplicate = [
        link
        for link in active_links
        if link.reviewed and link.method == "local_duplicate"
    ]
    if local_duplicate:
        return local_duplicate[0]
    return active_links[0] if active_links else None
