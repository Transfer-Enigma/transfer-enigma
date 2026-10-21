from collections.abc import Iterator
from pathlib import Path

import pytest
from backend_admin.resources import Resources
from module_shared.config import get_settings


@pytest.fixture
def isolated_resources_base_path(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("RESOURCES_BASE_PATH", raising=False)
    get_settings.cache_clear()
    Resources._base_path = None
    yield
    get_settings.cache_clear()
    Resources._base_path = None


def test_settings_value_wins(
    isolated_resources_base_path: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RESOURCES_BASE_PATH", str(tmp_path))
    assert Resources.get_base_path() == tmp_path.resolve()


def test_set_base_path_used_without_settings(
    isolated_resources_base_path: None, tmp_path: Path
) -> None:
    Resources.set_base_path(tmp_path)
    assert Resources.get_base_path() == tmp_path.resolve()
