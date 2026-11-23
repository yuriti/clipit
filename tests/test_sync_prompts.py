import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync_prompts", ROOT / "scripts" / "sync_prompts.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def tree(base: Path, files: dict):
    for name, text in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def test_copies_changes_and_removes_stale_files(tmp_path, monkeypatch, capsys):
    src, dst = tmp_path / "prompts", tmp_path / "bundled"
    tree(src, {"VERSION": "1.1.0\n", "vod/a.txt": "new", "fit/b.txt": "same", "schemas/s.json": "{}"})
    tree(dst, {"VERSION": "1.0.0\n", "vod/a.txt": "old", "vod/gone.txt": "x", "fit/b.txt": "same", "schemas/s.json": "{}"})
    monkeypatch.setattr(sync, "TARGET", dst)
    assert sync.main([str(src), "--check"]) == 1
    assert (dst / "vod/a.txt").read_text() == "old"           # --check changes nothing
    assert sync.main([str(src)]) == 0
    assert (dst / "vod/a.txt").read_text() == "new" and not (dst / "vod/gone.txt").exists()
    assert (dst / "VERSION").read_text() == "1.1.0\n"
    assert sync.main([str(src), "--check"]) == 0


def test_bundled_copy_matches_the_prompts_repository_when_it_is_next_door():
    source = ROOT.parent / "prompts"
    if not (source / "VERSION").exists():
        return  # the prompts repository is not checked out next to this one
    assert sync.plan(source) == [], "bundled prompts differ: run scripts/sync_prompts.py ../prompts"
