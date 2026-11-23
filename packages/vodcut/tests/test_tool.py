from importlib.metadata import entry_points

from smtv_core.tool import ENTRY_POINT_GROUP, Tool

from vodcut.tool import tool


def test_vodcut_is_a_tool():
    assert isinstance(tool, Tool) and tool.name == "vodcut"


def test_vodcut_is_found_by_smtv_when_installed():
    names = {ep.name: ep.value for ep in entry_points(group=ENTRY_POINT_GROUP)}
    assert names.get("vodcut") == "vodcut.tool:tool"


def test_a_stopped_run_is_printed_once(tmp_path, monkeypatch, capsys):
    import argparse

    from smtv_core.checks import OK, Check

    from vodcut import pipeline
    from vodcut import tool as tool_module

    monkeypatch.setattr(tool_module, "check_model", lambda s: Check("model", OK, "ok"))
    monkeypatch.setattr(tool_module.Settings, "load", classmethod(lambda cls, *a: cls()))

    def written(*_a, journal, **_k):              # the error went to the journal and was printed from there
        journal.emit("error", stage="analysis", message="no speech found in the recording")
        raise pipeline.RunError("no speech found in the recording")

    def not_written(*_a, **_k):                   # the journal itself failed: the command line still says why
        raise OSError("disk full")

    args = argparse.Namespace(out=str(tmp_path / "job"), source="x.mp4", language="ru", channel=None, workers=1, max_clips=None, no_render=True)
    for fake, expected in ((written, "Stopped: no speech found in the recording"), (not_written, "Stopped: OSError: disk full")):
        monkeypatch.setattr(pipeline, "run", fake)
        assert tool_module._cmd_run(args, {}, {}) == 1
        assert capsys.readouterr().out.splitlines() == [expected]


def test_a_recap_whose_encode_failed_is_exit_one_and_a_skipped_one_zero(tmp_path, monkeypatch):
    """C3: story.json alone does not make the recap a success."""
    import json
    from smtv_core.settings import Settings
    from vodcut import tool as vt
    job = tmp_path / "job"
    (job / "recap").mkdir(parents=True)
    (job / "clips.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(vt.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr("vodcut.recap.make", lambda *a, **k: None)
    (job / "recap" / "story.json").write_text(json.dumps({"status": "ok", "parts": []}), encoding="utf-8")
    assert vt._recap(job, Settings()) == 1
    (job / "recap" / "story.json").write_text(json.dumps({"status": "skipped"}), encoding="utf-8")
    assert vt._recap(job, Settings()) == 0
