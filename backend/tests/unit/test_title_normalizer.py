from music_manager_backend.domain.services.title_normalizer import normalize_title


def test_normalize_title_removes_case_spacing_and_punctuation() -> None:
    assert normalize_title(" Track  Name! ") == "track name"

