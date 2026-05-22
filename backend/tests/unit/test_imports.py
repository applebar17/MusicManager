from fastapi import FastAPI

from music_manager_backend.api.app import app, create_app


def test_backend_app_imports() -> None:
    assert app is not None
    assert isinstance(create_app(), FastAPI)
