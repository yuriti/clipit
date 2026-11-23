---
name: new-agent
description: Add or change a model agent of an SMTV tool — its prompt and answer schema in the prompts repository, its declaration (Agent, Needs), model recommendations, the anchor our server checks, and tests. Use when someone asks for a new prompt, a new model step, or to change what an agent asks the model.
---

# A new agent and its prompt

An agent is a prompt with its answer schema, the step it serves and what it needs from a model
(`smtv_core/agents.py`). Prompts live in the separate `prompts` repository (next to this one, `../prompts`) and are
copied in at a pinned version: never edit `smtv_core/prompts/` by hand.

## Steps

1. **Is it new?** Look at the agents already declared (`smtv_core.agents.CORE`, each tool's `Tool.agents`). An agent
   shared by several tools is declared once in the core (`core("layout")`), not copied per tool.
2. **Prompt and schema, in `../prompts`.** The prompt file (`vod/…-prompt.txt` or `fit/…`), its JSON schema in
   `schemas/`, a test case in `cases/<name>/`, a row in `models.json` (recommended model per provider; `ollama`
   column for local ones) and in the README's table. English prompt; text a viewer sees is written in the stream's
   language. Placeholders are replaced as plain text (`{channel}`), not by `str.format`.
3. **Run it** with the prompts harness against at least one real model (`prompttest`, see `../prompts/README.md`)
   and keep the run's answers out of git (`.runs/`).
4. **Release the prompts:** raise `VERSION` in `../prompts`, then here `python scripts/sync_prompts.py ../prompts`.
5. **Declare the agent** (`Agent`: `id`, `title`, `does`, `stage`, `prompt`, `schema`, `needs` with `level`, `images`,
   `why`). The page's «Settings → Agents» shows it by itself.
6. **Our server's anchor.** The StreamMoment provider accepts only prompts holding their agent's anchor:
   `packages/smtv-core/tests/test_account.py::ANCHORS` mirrors the server's list — a new agent needs its anchor on
   both sides; tell the maintainers, the server is not in this repository.
7. **Tests.** The answer validated against its schema (a good and a broken made-up answer), the step using the
   answer, the agent listed with its needs.
8. The `pre-pr-check` skill.
