"""Shared for the gateway's tests: a request starts whatever this computer's checks say (stage 24 blocks new requests while
a check fails, and a test computer has no model set up). Tests of that blocking are marked `doctor` and keep it."""
import pytest


@pytest.fixture(autouse=True)
def _checks_do_not_block(request, monkeypatch):
    if request.node.get_closest_marker("doctor"):
        return
    from smtv import serve
    monkeypatch.setattr(serve.App, "not_ready", lambda self, name: None)
