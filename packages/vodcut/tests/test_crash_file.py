"""An unexpected error in a VodCut job leaves a crash file for «Report a problem»; an expected stop (RunError) does not."""
import json

import pytest

from smtv_core import crash
from smtv_core.events import Journal
from vodcut import tool
from vodcut.pipeline import RunError


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(crash, "_recent", {})


def test_unexpected_error_leaves_a_crash_file_with_the_step(tmp_path):
    job = tmp_path / "v123"
    with Journal(job, tool="vodcut", subscribers=[]) as journal:
        journal.emit("stage", name="speech", step=3, steps=6)
        try:
            raise IndexError("list index out of range")
        except IndexError as e:
            tool._crash(e, job, journal)
    data = json.loads(crash.files()[0].read_text(encoding="utf-8"))
    assert (data["where"], data["tool"], data["job"], data["stage"], data["type"]) == ("job", "vodcut", "v123", "speech", "IndexError")


def test_expected_stop_is_not_a_crash(tmp_path):
    job = tmp_path / "v124"
    with Journal(job, tool="vodcut", subscribers=[]) as journal:
        tool._crash(RunError("the link does not open"), job, journal)
    assert crash.files() == []
