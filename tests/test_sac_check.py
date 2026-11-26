"""install/app/sac_check.py and the workflow smart-app-control.yml: SMTV under a policy like Smart App Control."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "install" / "app"))
try:
    import sac_check
finally:
    sys.path.remove(str(REPO / "install" / "app"))

WORKFLOW = (REPO / ".github" / "workflows" / "smart-app-control.yml").read_text(encoding="utf-8")

EVENTS = """<Events>
<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>3077</EventID>
<TimeCreated SystemTime='2026-11-26T20:00:01.000Z'/></System><EventData>
<Data Name='File Name'>\\Device\\HarddiskVolume3\\Users\\x\\AppData\\Local\\Temp\\is-AB12.tmp\\SMTV-windows-setup.tmp</Data>
<Data Name='Process Name'>\\Device\\HarddiskVolume3\\a\\SMTV-windows-setup.exe</Data>
<Data Name='PolicyName'>SMTV check: SmartAppControl.xml</Data></EventData></Event>
<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>3089</EventID>
<TimeCreated SystemTime='2026-11-26T20:00:01.100Z'/></System><EventData><Data Name='Publisher'></Data></EventData></Event>
<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>3033</EventID>
<TimeCreated SystemTime='2026-11-26T20:00:02.000Z'/></System><EventData>
<Data Name='FileName'>\\Device\\HarddiskVolume3\\a\\zip\\SMTV\\python312.dll</Data>
<Data Name='ProcessName'>\\Device\\HarddiskVolume3\\a\\zip\\SMTV\\SMTV.exe</Data></EventData></Event>
<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>3077</EventID>
<TimeCreated SystemTime='2026-11-26T20:00:03.000Z'/></System><EventData>
<Data Name='File Name'>\\Device\\HarddiskVolume3\\Users\\x\\AppData\\Local\\Temp\\is-AB12.tmp\\SMTV-windows-setup.tmp</Data>
</EventData></Event>
</Events>"""


def test_the_events_name_the_blocked_file_whatever_their_id_calls_it():
    events = sac_check.parse_events(EVENTS)
    assert [e["id"] for e in events] == [3077, 3089, 3033, 3077]
    assert events[0]["policy"] == "SMTV check: SmartAppControl.xml" and events[2]["process"].endswith("SMTV.exe")
    blocked = sac_check.blocked_files(events)          # once each, the informational 3089 left out
    assert [Path(f.replace("\\", "/")).name for f in blocked] == ["SMTV-windows-setup.tmp", "python312.dll"]
    assert sac_check.parse_events("") == []


def test_a_program_windows_refuses_to_start_counts_as_blocked(monkeypatch):
    # what Yuri saw: «Error 4551: an Application Control policy has blocked this file»
    def refuse(*a, **k):
        e = OSError("[WinError 4551] An Application Control policy has blocked this file")
        e.winerror = 4551
        raise e
    monkeypatch.setattr(sac_check.subprocess, "run", refuse)
    monkeypatch.setattr(sac_check, "events_since", lambda t: [])
    case = sac_check.run_case("b1", "the ZIP's SMTV.exe starts", ["SMTV.exe"], 5)
    assert case["blocked"] and not case["ok"] and "4551" in case["output"]
    assert sac_check.verdict(case) == "BLOCKED"


def test_a_failure_with_no_block_is_not_put_on_the_policy(monkeypatch):
    monkeypatch.setattr(sac_check.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "No module named numpy"))
    monkeypatch.setattr(sac_check, "events_since", lambda t: [])
    case = sac_check.run_case("c3", "libraries load", ["python", "-c", "x"], 5)
    assert not case["blocked"] and sac_check.verdict(case) == "failed (not by the policy)"
    # a block event during the run marks it, even when the program said nothing
    monkeypatch.setattr(sac_check, "events_since", lambda t: sac_check.parse_events(EVENTS))
    case = sac_check.run_case("c3", "libraries load", ["python", "-c", "x"], 5)
    assert case["blocked"] and len(case["blocked_by"]) == 2


def test_the_control_decides_whether_anything_else_means_something(monkeypatch, tmp_path):
    monkeypatch.setattr(sac_check, "events_since", lambda t: [])
    ran = {"name": "0", "what": "control", "blocked": False, "blocked_by": [], "events": [], "command": "c", "ok": False}
    assert sac_check.verdict(ran) == "NOT blocked: the policy is not enforced"
    assert sac_check.verdict({**ran, "blocked": True}) == "blocked: the policy is on"
    text = sac_check.report([{**ran, "blocked": True}], "SmartAppControl.xml (enforced)", "")
    assert "| 0 | control | blocked: the policy is on | - |" in text and "Policy: SmartAppControl.xml" in text


def test_the_signatures_are_counted_by_signer_and_the_unsigned_by_package():
    root = "C:\\a\\zip\\SMTV"
    ms = "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US"
    rows = [{"root": root, "path": root + "\\SMTV.exe", "status": "NotSigned", "signer": ""},
            {"root": root, "path": root + "\\python312.dll", "status": "NotSigned", "signer": ""},
            {"root": root, "path": root + "\\Lib\\site-packages\\numpy\\_core\\x.pyd", "status": "NotSigned", "signer": ""},
            {"root": root, "path": root + "\\Lib\\site-packages\\onnxruntime\\capi\\onnxruntime.dll", "status": "Valid",
             "signer": ms}]
    if sys.platform != "win32":       # the paths above are Windows ones
        for r in rows:
            r["root"], r["path"] = r["root"].replace("\\", "/"), r["path"].replace("\\", "/")
    text = sac_check.summarize_signatures(rows)
    assert "| NotSigned | - | 3 |" in text and "| Valid | Microsoft Corporation | 1 |" in text
    assert re.search(r"\| SMTV\.exe \| NotSigned \| - \|", text)
    assert "numpy 1" in text and "(top folder) 2" in text
    assert sac_check.common_name(ms) == "Microsoft Corporation"


def test_the_workflow_runs_by_hand_enforces_the_policy_and_checks_all_three_ways():
    assert "workflow_dispatch:" in WORKFLOW and "release:" not in WORKFLOW and "push:" not in WORKFLOW
    assert "SmartAppControl.xml" in WORKFLOW and "SignedReputable.xml" in WORKFLOW
    assert "-Option 3 -Delete" in WORKFLOW and "CiTool.exe --update-policy" in WORKFLOW     # enforced, not audit
    assert "ResetPolicyID" in WORKFLOW                       # never Windows' own Smart App Control policy id
    assert "install/app/sac_check.py signatures" in WORKFLOW and "install/app/sac_check.py run" in WORKFLOW
    # the release's file names are those release.yml puts on every release
    release = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    for name in ("SMTV-windows-setup.exe", "SMTV-windows.zip"):
        assert f"--pattern '{name}'" in WORKFLOW and f"dist/latest/{name}" in release
    # an input reaches the shell only through the environment (no template injection)
    for line in WORKFLOW.splitlines():
        if "${{ inputs." in line:
            assert line.strip().startswith("TAG:"), line
    assert "permissions:\n  contents: read" in WORKFLOW and "persist-credentials: false" in WORKFLOW
    for action in re.findall(r"uses: (\S+)", WORKFLOW):
        assert re.search(r"@[0-9a-f]{40}$", action), action
