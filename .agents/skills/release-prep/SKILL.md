---
name: release-prep
description: Prepare an SMTV release — versions agreed across packages, prompts pinned, every check green, third-party licenses and SBOM, changelog, nothing personal in the history. Use when a maintainer asks to prepare, cut or check a release. Publishing itself is the maintainer's step.
---

# Preparing a release

1. **What goes out.** `git log <last tag>..main --oneline`; group the changes for people (new, fixed, changed).
2. **Versions.** `smtv`, `smtv-core` and `vodcut` always come out together under one number (owner's decision 22.11):
   one change raises all three (`packages/*/pyproject.toml`) and the pins between them (`smtv-core==…` in `smtv` and
   `vodcut`, the extras in `packages/smtv/pyproject.toml`); `uv lock`.
3. **Prompts.** The bundled prompts equal a released version of `../prompts` (`python scripts/sync_prompts.py
   ../prompts --check`), its `VERSION` tagged there.
4. **Checks.** `uv run python scripts/check.py --ci` on a clean tree with the private word list present. Every check
   runs; a skip is a failure here. Then `python scripts/check.py licenses --write` and read `THIRD_PARTY_LICENSES.md`:
   models with CC-BY are credited in the window's «About».
5. **History.** Every commit author is a noreply address (`traces` checks it); no personal word anywhere in the
   history (`gitleaks git`, the private list over `git log -p`).
6. **Changelog**: a new section on top of `CHANGELOG.md` and the same text in the release notes — what a person
   notices, in plain words, with credit to contributors by their GitHub login.
7. **Installers.** `install/install.sh` and `install/install.ps1` still install this version (`pytest
   tests/test_install_scripts.py`; on a Mac `brew install shellcheck` first so its test runs).
8. **Hand over.** Tag, GitHub release and PyPI upload are the maintainer's: the `sbom` workflow attaches the SBOM and
   the licenses file to the release by itself.
