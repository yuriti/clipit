"""Asking the model: one call, its answer checked against the schema, and a record of what it cost."""
from __future__ import annotations

import threading
from typing import Callable

from jsonschema import Draft202012Validator
from smtv_core.events import MODEL_CALL, Journal
from smtv_core.llm import Overloaded, ProviderError, QuotaExceeded, call
from smtv_core.settings import ModelSettings


class Asker:
    """Shared by the threads of one run. A QuotaExceeded stops every later call: retrying cannot help.

    With a journal every call is written to it as a model_call event: what it was for, the model, time, tokens, and the
    error if any. `models` gives the model for a call's purpose (each agent its own, stage 10: `smtv_core.agents.models_for`);
    without it every call uses `model`.
    """

    def __init__(self, model: ModelSettings, caller=call, journal: Journal | None = None,
                 models: Callable[[str], ModelSettings] | None = None):
        self.model, self.caller, self.journal, self.models = model, caller, journal, models
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.tokens_in = self.tokens_out = self.calls = 0
        self.quota_error: str | None = None

    def model_for(self, purpose: str) -> ModelSettings:
        return self.models(purpose) if self.models else self.model

    def ask(self, prompt: str, schema: dict, images=None, *, purpose: str = "") -> tuple[dict | None, dict]:
        """(answer or None, meta). meta has 'error' when there is no usable answer."""
        model = self.model_for(purpose)
        answer, meta = self._ask(model, prompt, schema, images)
        if self.journal is not None and meta.get("error") != "stopped":  # a stopped run makes no call
            self.journal.emit(MODEL_CALL, purpose=purpose, model=f"{model.provider}/{model.model or 'default'}",
                              images=len(images or ()), **{k: v for k, v in meta.items() if v is not None})
        return answer, meta

    def _ask(self, model: ModelSettings, prompt: str, schema: dict, images=None) -> tuple[dict | None, dict]:
        if self.stop.is_set():
            return None, {"error": "stopped"}
        try:
            answer = self.caller(model, prompt, schema, images) if images else self.caller(model, prompt, schema)
        except QuotaExceeded as e:
            with self.lock:
                self.quota_error = str(e)
            self.stop.set()
            return None, {"error": f"quota: {e}"[:300]}
        except Overloaded as e:
            return None, {"error": f"busy: {e}"[:300]}
        except ProviderError as e:
            return None, {"error": f"model: {e}"[:300]}
        with self.lock:
            self.calls += 1
            self.tokens_in += answer.tokens_in or 0
            self.tokens_out += answer.tokens_out or 0
        meta = {"seconds": round(answer.seconds, 1), "tokens_in": answer.tokens_in, "tokens_out": answer.tokens_out,
                "cost_usd": model.cost(answer.tokens_in, answer.tokens_out)}
        errors = sorted(Draft202012Validator(schema).iter_errors(answer.data), key=lambda e: list(e.absolute_path))
        if errors:
            meta["schema_errors"] = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:120]}" for e in errors[:5]]
        return answer.data if isinstance(answer.data, dict) else None, meta
