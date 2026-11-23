import json
import threading

import pytest

from smtv_core import events
from smtv_core.events import Journal


def test_numbers_time_type_and_data(tmp_path):
    j = Journal(tmp_path / "job", tool="t", subscribers=[])
    a = j.emit("stage", name="audio", step=1)
    b = j.emit("progress", stage="speech", percent=10)
    assert (a["n"], b["n"]) == (1, 2) and a["t"] <= b["t"] and j.last == 2
    lines = [json.loads(x) for x in (tmp_path / "job" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines == [a, b] and lines[0]["type"] == "stage" and lines[0]["data"] == {"name": "audio", "step": 1}
    assert a["v"] == events.VERSION and a["job"] == "job" and a["tool"] == "t"


def test_unknown_type_is_refused(tmp_path):
    with pytest.raises(ValueError):
        Journal(tmp_path, tool="t", subscribers=[]).emit("stagee")


def test_a_rerun_continues_the_numbers(tmp_path):
    Journal(tmp_path, tool="t", subscribers=[]).emit("stage", name="audio")
    Journal(tmp_path, tool="t", subscribers=[]).emit("stage", name="speech")
    again = Journal(tmp_path, tool="t", subscribers=[])
    assert again.last == 2 and again.emit("done")["n"] == 3
    assert [e["n"] for e in events.read(tmp_path)] == [1, 2, 3]


def test_read_after_a_number(tmp_path):
    j = Journal(tmp_path, tool="t", subscribers=[])
    for i in range(5):
        j.emit("progress", i=i)
    assert [e["data"]["i"] for e in events.read(tmp_path, after=3)] == [3, 4]
    assert j.read(after=5) == [] and len(events.read(tmp_path / "events.jsonl")) == 5
    (tmp_path / "empty").mkdir()
    assert events.read(tmp_path / "empty") == []                # a job that has not started yet


def test_a_line_being_written_is_not_read_and_a_torn_line_is_closed(tmp_path):
    j = Journal(tmp_path, tool="t", subscribers=[])
    j.emit("stage", name="audio")
    with (tmp_path / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"n": 2, "t": 1, "type": "prog')  # the writer is in the middle of a line, or crashed there
    assert [e["n"] for e in events.read(tmp_path)] == [1]
    again = Journal(tmp_path, tool="t", subscribers=[])
    assert again.emit("stage", name="speech")["n"] == 2
    assert [e["data"]["name"] for e in events.read(tmp_path)] == ["audio", "speech"]


def test_many_threads_write_whole_lines_with_unique_numbers(tmp_path):
    seen = []
    j = Journal(tmp_path, tool="t", echo=seen.append, subscribers=[])

    def write(k):
        for i in range(200):
            j.emit("model_call", thread=k, i=i, text="x" * 500)

    threads = [threading.Thread(target=write, args=(k,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    got = events.read(tmp_path)
    assert [e["n"] for e in got] == list(range(1, 1601))         # every line whole, numbers in file order without gaps
    assert [e["n"] for e in seen] == list(range(1, 1601))        # the command line sees them in the same order
    assert len((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()) == 1600


def test_the_contract_is_versioned_and_names_every_type():
    from smtv_core.events import contract
    assert set(contract.types()) == set(events.TYPES) and contract.version() == events.VERSION
    major, minor = events.VERSION.split(".")
    assert major.isdigit() and minor.isdigit()
    good = {"n": 1, "t": 1.0, "type": "clip_ready", "v": events.VERSION, "job": "j", "tool": "t", "data": {"clip": "clip01", "file": "clips/clip01.mp4"}}
    assert contract.validate(good) == [] and contract.undeclared(good) == []
    assert contract.validate({**good, "data": {"clip": "clip01"}})            # a required field is missing
    assert contract.validate({**good, "job": None})                            # the envelope is checked too
    assert contract.validate({**good, "data": {**good["data"], "later": 1}}) == []   # readers accept fields of a newer minor version
    assert contract.undeclared({**good, "data": {**good["data"], "later": 1}}) == ["later"]


def wait_for(cond, seconds=5.0):
    import time
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_subscribers_get_every_event_and_a_failing_or_slow_one_does_not_hurt_the_job(tmp_path):
    import time
    got, slow_got = [], []
    release = threading.Event()

    def good(event):
        got.append(event["n"])

    def broken(event):
        raise RuntimeError("cannot reach the server")

    def slow(event):
        release.wait(5)
        slow_got.append(event["n"])

    j = Journal(tmp_path, tool="t", subscribers=[("good", good), ("broken", broken), ("slow", slow)])
    started = time.monotonic()
    for i in range(50):
        j.emit("progress", stage="x", done=i)
    assert time.monotonic() - started < 1.0                                    # the slow subscriber does not hold the job up
    release.set()
    j.close()
    written = events.read(tmp_path)
    errors = [e for e in written if e["type"] == "error"]
    assert len(errors) == 1 and errors[0]["data"]["subscriber"] == "broken" and "cannot reach" in errors[0]["data"]["message"]
    assert got == [e["n"] for e in written] and slow_got == got                # in order, including the error event itself


def test_a_subscriber_catches_up_from_a_number_with_no_gap_and_no_repeat(tmp_path):
    j = Journal(tmp_path, tool="t", subscribers=[])
    for i in range(5):
        j.emit("progress", stage="x", done=i)
    got = []
    j.subscribe(lambda e: got.append(e["n"]), after=2)
    for i in range(3):
        j.emit("progress", stage="x", done=i)
    j.close()
    assert got == [3, 4, 5, 6, 7, 8]


def test_installed_subscribers_are_loaded_and_a_broken_one_is_skipped(tmp_path, monkeypatch):
    from smtv_core.events import subscribers

    class EP:
        def __init__(self, name, value):
            self.name, self.value = name, value

        def load(self):
            if isinstance(self.value, Exception):
                raise self.value
            return self.value

    seen = []
    monkeypatch.setattr(subscribers, "entry_points", lambda group: [EP("ok", seen.append), EP("bad", ImportError("missing package"))]
                        if group == subscribers.ENTRY_POINT_GROUP else [])
    j = Journal(tmp_path, tool="t")
    j.emit("stage", name="audio")
    j.close()
    assert [e["type"] for e in seen] == ["stage"]
