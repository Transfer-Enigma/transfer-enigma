"""The architecture rules of the project, checked by the test suite.

The layers may only depend on each other downwards:

    entrypoints/  ->  services/  ->  data/  ->  shared/

A test that breaks these rules breaks the architecture, so they are
checked here.
"""

import ast
from pathlib import Path

import pytest

APPS = Path(__file__).parent.parent / "apps"

# The packages of every layer, relative to the apps directory.
LAYERS = {
    "entrypoints": ("entrypoints/user", "entrypoints/admin", "entrypoints/auth"),
    "services": ("services",),
    "data": ("data",),
    "shared": ("shared",),
}

FORBIDDEN_IN_SERVICES = {
    "fastapi",
    "starlette",
    "sqlalchemy",
}

# The data the services may not reach directly, they use the protocols.
FORBIDDEN_IN_SERVICES_DATA = (
    "data.repositories",
    "data.internal",
    "data.fesco",
    "data.sources",
)

FORBIDDEN_IN_DATA = (
    "services",
    "entrypoints",
)

FORBIDDEN_IN_ENTRYPOINTS = (
    "data.internal",
    "data.fesco",
    "data.sources",
)


def _packages_of(path: Path) -> list[str]:
    """The top level packages a file belongs to."""
    relative = path.relative_to(APPS)
    return list(relative.parts[:-1])


def _imported_modules(path: Path) -> list[tuple[str, list[str]]]:
    """The modules a file imports, with the names it takes from them."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[tuple[str, list[str]]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append((alias.name, []))
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            names = [alias.name for alias in node.names]
            imported.append((node.module, names))

    return imported


def _files_of_layer(layer: str) -> list[Path]:
    files: list[Path] = []
    for name in LAYERS[layer]:
        root = APPS / name
        if not root.is_dir():
            continue
        files.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _all_files() -> list[Path]:
    return sorted(p for p in APPS.rglob("*.py") if "__pycache__" not in p.parts)


def test_services_do_not_import_the_web_framework_or_the_orm():
    """The services must be usable outside of a request and of a session."""
    offenders = []
    for path in _files_of_layer("services"):
        for module, _names in _imported_modules(path):
            if module.split(".")[0] in FORBIDDEN_IN_SERVICES:
                offenders.append(f"{path.name} imports {module}")

    assert not offenders, "services must not import the web framework or the ORM: " + ", ".join(offenders)


def test_services_reach_the_data_through_the_protocols():
    """The services talk to the sources through the protocols."""
    offenders = []
    for path in _files_of_layer("services"):
        for module, _names in _imported_modules(path):
            if module.startswith(FORBIDDEN_IN_SERVICES_DATA):
                offenders.append(f"{path.name} imports {module}")

    assert not offenders, "services must not reach the data directly: " + ", ".join(offenders)


def test_data_does_not_import_the_layers_above():
    """The data layer must not know who uses it."""
    offenders = []
    for path in _files_of_layer("data"):
        for module, _names in _imported_modules(path):
            if module.split(".")[0] in FORBIDDEN_IN_DATA:
                offenders.append(f"{path.name} imports {module}")

    assert not offenders, "the data layer must not import the layers above: " + ", ".join(offenders)


def test_entrypoints_do_not_import_a_concrete_source():
    """The entrypoints talk to the sources through the protocols."""
    offenders = []
    for path in _files_of_layer("entrypoints"):
        for module, _names in _imported_modules(path):
            if module.startswith(FORBIDDEN_IN_ENTRYPOINTS):
                offenders.append(f"{path.name} imports {module}")

    assert not offenders, "the entrypoints must not import a concrete source: " + ", ".join(offenders)


def test_no_private_symbol_is_imported_across_the_packages():
    """A private helper stays inside the package that owns it."""
    offenders = []
    for path in _all_files():
        packages = _packages_of(path)
        own_package = packages[0] if packages else ""

        for module, names in _imported_modules(path):
            if not module:
                continue
            other_package = module.split(".")[0]
            if other_package == own_package or other_package not in LAYERS:
                continue
            for name in names:
                if name.startswith("_"):
                    offenders.append(f"{path.name} imports {name} from {module}")

    assert not offenders, "a private symbol must not cross the packages: " + ", ".join(offenders)


@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_every_layer_has_files(layer):
    """A layer that lost its files is a layer that was removed by accident."""
    assert _files_of_layer(layer), f"the layer '{layer}' has no files"
