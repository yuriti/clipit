---
name: new-tool
description: Add a new SMTV tool (a plugin like VodCut) — its package, entry point, commands, checks, page section, catalog line and tests. Use when someone asks to create a new tool, plugin or «cube» for SMTV.
---

# A new SMTV tool

A tool is its own package in `packages/<name>/`, published to PyPI on its own, plugged into `smtv` through an entry
point. Read `AGENTS.md` (root) and `packages/vodcut/AGENTS.md` first: VodCut is the reference tool.

## Steps

1. **Is it new?** Search `packages/*/src` and `smtv_core` for what it would do. Shared work (models, speech,
   rendering, downloads, settings, checks) already lives in `smtv_core`; the tool only adds its own steps. If an
   existing tool can grow instead, propose that (REVIEW.md, «one task, one way»).
2. **Package.** `packages/<name>/pyproject.toml` like VodCut's: `license = "MIT"`, `license-files`, hatchling,
   dependency `smtv-core==<the workspace version>`, entry point `[project.entry-points."smtv.tools"] <name> =
   "<name>.tool:tool"`. Add it to `members` in the root `pyproject.toml`, `[tool.uv.sources]`, the pytest
   `testpaths`, and `source-dirs` in `[tool.smtv-check]`. New dependencies: allowed licenses only, the reason in the PR.
3. **The contract.** `<name>/tool.py` returns `smtv_core.tool.Tool`: `name`, `summary`, `version`, `add_commands`,
   `checks` (each failing check says how to fix it in one step), and `page` if it has a section in the window.
   Import shared code only from `smtv_core`, never from another tool.
4. **Events.** Every step reports through the job's journal (`smtv_core.events.Journal`), never `print`. New event
   types and fields go into `smtv_core/events/schema.json` (a new field raises the minor version).
5. **Catalog.** A line in `CATALOG` (`packages/smtv/src/smtv/tools.py`) and an extra in
   `packages/smtv/pyproject.toml` (`<name> = ["<name>==<version>"]`, and in `all`).
6. **Agents and prompts**, if the tool calls a model: the `new-agent` skill.
7. **Tests.** `packages/<name>/tests/`: the tool loads through the entry point, `smtv` keeps working when the tool
   fails to load, each command on a made-up input, each check failing and passing.
8. **Docs.** `packages/<name>/AGENTS.md` (how it works, its rules), `packages/<name>/README.md`, a line in the root
   README's tool list.
9. `uv lock`, then the `pre-pr-check` skill.
