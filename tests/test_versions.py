"""Keep the packages and their dependencies on the same release."""

import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("smtv", "smtv-core", "vodcut")


def test_package_versions_are_in_sync():
    versions = {}
    for package in PACKAGES:
        directory = ROOT / "packages" / package
        with (directory / "pyproject.toml").open("rb") as file:
            versions[package] = tomllib.load(file)["project"]["version"]
        module = directory / "src" / package.replace("-", "_") / "__init__.py"
        assignments = ast.parse(module.read_text()).body
        init_version = next(
            ast.literal_eval(node.value)
            for node in assignments
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
        )
        assert init_version == versions[package], f"{module}: update __version__ to {versions[package]}"

    assert len(set(versions.values())) == 1, f"Update package versions to match: {versions}"
    version = versions["smtv"]
    pattern = re.compile(r"^\s*(smtv-core|smtv|vodcut)(?:\[[^\]]+\])?\s*==\s*([^\s;]+)", re.IGNORECASE)

    def check_values(value, path):
        if isinstance(value, dict):
            for child in value.values():
                check_values(child, path)
        elif isinstance(value, list):
            for child in value:
                check_values(child, path)
        elif isinstance(value, str):
            match = pattern.match(value)
            if match:
                assert match.group(2) == version, f"{path}: update {value} to {version}"

    for path in ROOT.rglob("pyproject.toml"):
        if {".venv", ".claude"} & set(path.relative_to(ROOT).parts):
            continue
        with path.open("rb") as file:
            check_values(tomllib.load(file), path)
