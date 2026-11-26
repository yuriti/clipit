"""SMTV under an App Control policy like Smart App Control (Windows 11), for the workflow smart-app-control.yml.

    python install/app/sac_check.py signatures --out sig.json DIR...     # before the policy: who signed which file
    python install/app/sac_check.py run --work DIR --repo .              # under the policy: what runs, what is blocked

`run` tries, each on its own: a fresh unsigned program (it must be blocked, or the policy is not on and nothing else
means anything); the release's installer, installed silently; the ZIP's SMTV.exe and its full check (smoke.py); the app
installed before the policy; the one-line install/install.ps1 of this branch, then `python -m smtv doctor`, the heavy
libraries with the window's bridge (pythonnet), `smtv serve` and the window. For each: blocked or not, by which file,
with the CodeIntegrity events Windows wrote meanwhile. Writes report.md (also the job summary) and report.json.
Runs on python.org's Python, which is signed: PowerShell under such a policy runs unsigned scripts in a restricted mode.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG = "Microsoft-Windows-CodeIntegrity/Operational"
BLOCKED_IDS = {3033, 3077}          # enforced: below the signing level / against the policy
AUDIT_IDS = {3034, 3076}            # the same in audit mode (would have been blocked)
ERROR_POLICY_BLOCKED = 4551         # «An Application Control policy has blocked this file»
NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
KEY_FILES = ("SMTV.exe", "python.exe", "pythonw.exe", "python3.dll", "python312.dll", "ffmpeg.exe", "ffprobe.exe",
             "unins000.exe", "Python.Runtime.dll", "ClrLoader.dll", "WebView2Loader.dll", "onnxruntime.dll")

PROBE = r"""
import onnxruntime, av, numpy, ctranslate2, onnx_asr, webview
import clr                                     # pythonnet: .NET, the bridge to SMTV's window on Windows
from webview.platforms import winforms         # noqa: F401 — loads WinForms and WebView2
print("loaded")
"""

SIGNATURES_PS = r"""
$ErrorActionPreference = 'Stop'
$rows = foreach ($d in $args) {
  # by extension: an Include filter with LiteralPath keeps every file, and the others come back as UnknownError
  Get-ChildItem -LiteralPath $d -Recurse -File | Where-Object { $_.Extension -in '.exe', '.dll', '.pyd' } |
  Get-AuthenticodeSignature | ForEach-Object {
    [pscustomobject]@{ root = $d; path = $_.Path; status = "$($_.Status)";
                       signer = $(if ($_.SignerCertificate) { $_.SignerCertificate.Subject } else { '' }) } } }
$rows | ConvertTo-Json -Compress -Depth 3
"""


def windows_env(**extra: str) -> dict[str, str]:
    """This environment for Windows PowerShell 5.1 and what it starts: without PSModulePath, which the workflow's
    PowerShell 7 sets to its own modules (5.1 then cannot load even Get-AuthenticodeSignature). A person's PowerShell
    window has none of it either."""
    env = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
    env.update(extra)
    return env


# --- the CodeIntegrity journal ---------------------------------------------------------------------------------------

def stamp(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_events(xml_text: str) -> list[dict]:
    """wevtutil's events as {id, time, file, process, policy}: the names Windows gives them differ between event ids."""
    out = []
    if not xml_text.strip():
        return out
    root = ET.fromstring(xml_text if xml_text.lstrip().startswith("<Events") else f"<Events>{xml_text}</Events>")
    for ev in root.iter(f"{{{NS['e']}}}Event"):
        eid = int(ev.findtext("e:System/e:EventID", default="0", namespaces=NS))
        created = ev.find("e:System/e:TimeCreated", NS)
        data = {d.get("Name", ""): (d.text or "") for d in ev.iterfind("e:EventData/e:Data", NS)}
        out.append({"id": eid, "time": created.get("SystemTime", "") if created is not None else "",
                    "file": data.get("File Name") or data.get("FileName") or "",
                    "process": data.get("Process Name") or data.get("ProcessName") or "",
                    "policy": data.get("PolicyName") or data.get("Policy Name") or ""})
    return out


def events_since(t: datetime) -> list[dict]:
    query = f"*[System[TimeCreated[@SystemTime>='{stamp(t)}']]]"
    r = subprocess.run(["wevtutil", "qe", LOG, f"/q:{query}", "/f:xml", "/e:Events"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        return [{"id": 0, "time": "", "file": f"wevtutil failed: {r.stderr.strip()[:300]}", "process": "", "policy": ""}]
    return parse_events(r.stdout)


def blocked_files(events: list[dict]) -> list[str]:
    seen: list[str] = []
    for e in events:
        if e["id"] in BLOCKED_IDS and e["file"] and e["file"] not in seen:
            seen.append(e["file"])
    return seen


# --- one case --------------------------------------------------------------------------------------------------------

def finish(case: dict, started: datetime) -> dict:
    case["events"] = events_since(started)
    case["blocked_by"] = blocked_files(case["events"])
    case["blocked"] = case.get("blocked", False) or bool(case["blocked_by"])
    return case


def run_case(name: str, what: str, argv: list[str], timeout: float, ok=None, **kw) -> dict:
    """Runs one program to its end; ok(result) says whether what it should do happened."""
    started = datetime.now(timezone.utc) - timedelta(seconds=1)
    case: dict = {"name": name, "what": what, "command": " ".join(argv)}
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           **kw)
        case.update(exit=r.returncode, output=(r.stdout + r.stderr)[-3000:])
        case["ok"] = bool(ok(r)) if ok else r.returncode == 0
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        case.update(exit=None, ok=False, output=f"still running after {timeout:.0f} s (a message box?)\n{out[-2000:]}")
    except OSError as e:
        code = getattr(e, "winerror", None)
        case.update(exit=None, ok=False, output=f"did not start: {e}", blocked=code == ERROR_POLICY_BLOCKED)
    return finish(case, started)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve_case(python: str, env: dict) -> dict:
    started = datetime.now(timezone.utc) - timedelta(seconds=1)
    port = free_port()
    case: dict = {"name": "c4", "what": "`smtv serve` answers /api/hello", "command": f"{python} -m smtv serve"}
    try:
        p = subprocess.Popen([python, "-m", "smtv", "serve", "--no-browser", "--port", str(port)], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace")
    except OSError as e:
        case.update(exit=None, ok=False, output=f"did not start: {e}", blocked=getattr(e, "winerror", 0) == ERROR_POLICY_BLOCKED)
        return finish(case, started)
    answer = None
    end = time.monotonic() + 120
    while time.monotonic() < end and p.poll() is None and answer is None:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hello", timeout=3) as r:   # noqa: S310 — local
                answer = json.loads(r.read())
        except (OSError, ValueError):
            time.sleep(1)
    p.terminate()
    try:
        out, _ = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    case.update(exit=p.returncode, ok=bool(answer and answer.get("app") == "smtv"), output=f"/api/hello: {answer}\n{out[-2000:]}")
    return finish(case, started)


def window_case(pythonw: str, env: dict, wait_s: float = 45) -> dict:
    """The window: still open after `wait_s` seconds (pythonw shows no output; a crash ends it sooner)."""
    started = datetime.now(timezone.utc) - timedelta(seconds=1)
    case: dict = {"name": "c5", "what": f"the window (`pythonw -m smtv app`) still open after {wait_s:.0f} s",
                  "command": f"{pythonw} -m smtv app"}
    try:
        p = subprocess.Popen([pythonw, "-m", "smtv", "app"], env=env)
    except OSError as e:
        case.update(exit=None, ok=False, output=f"did not start: {e}", blocked=getattr(e, "winerror", 0) == ERROR_POLICY_BLOCKED)
        return finish(case, started)
    time.sleep(wait_s)
    alive = p.poll() is None
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    case.update(exit=None if alive else p.returncode, ok=alive, output="open" if alive else f"ended with {p.returncode}")
    return finish(case, started)


# --- the cases -------------------------------------------------------------------------------------------------------

def uv_python(env: dict) -> tuple[str, str] | None:
    """python.exe and pythonw.exe of the SMTV that install.ps1 made (uv's tool folder)."""
    uv = shutil.which("uv", path=env.get("PATH")) or str(Path.home() / ".local" / "bin" / "uv.exe")
    try:
        tools = subprocess.run([uv, "tool", "dir"], capture_output=True, text=True, timeout=60, env=env).stdout.strip()
    except OSError:
        return None
    scripts = Path(tools) / "smtv" / "Scripts"
    return (str(scripts / "python.exe"), str(scripts / "pythonw.exe")) if (scripts / "python.exe").is_file() else None


def run_all(work: Path, repo: Path) -> list[dict]:
    cases = []
    control = work / "control.exe"
    cases.append(run_case("0", "a fresh unsigned program is blocked (the policy is on)", [str(control)], 60,
                          ok=lambda r: False))
    cases[-1]["ok"] = cases[-1]["blocked"]

    setup = work / "SMTV-windows-setup.exe"
    target = work / "installed-under-policy"
    cases.append(run_case("a", "the installer installs silently", [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                          "/NORESTART", f"/DIR={target}", f"/LOG={work / 'setup.log'}"], 600,
                          ok=lambda r: r.returncode == 0 and (target / "SMTV.exe").is_file()))

    app = work / "zip" / "SMTV"
    cases.append(run_case("b0", "the ZIP's ffmpeg on its own (Gyan's build, not signed: does reputation let it run?)",
                          [str(app / "ffmpeg" / "ffmpeg.exe"), "-hide_banner", "-version"], 120,
                          ok=lambda r: r.returncode == 0 and "ffmpeg version" in r.stdout))
    marker = work / "zip-ran.txt"
    cases.append(run_case("b1", "the ZIP's SMTV.exe starts", [str(app / "SMTV.exe"), "-c",
                          f"open(r'{marker}', 'w').write('ok')"], 120, ok=lambda r: marker.is_file()))
    smoke = str(repo / "install" / "app" / "smoke.py")
    cases.append(run_case("b2", "the ZIP's full check (smoke.py: libraries, ffmpeg, doctor, serve)",
                          [sys.executable, smoke, str(app), "--kind", "zip"], 900))
    before = work / "installed"
    if (before / "python.exe").is_file():
        cases.append(run_case("b3", "the app installed before the policy, its full check",
                              [sys.executable, smoke, str(before), "--kind", "exe"], 900))

    env = windows_env(SMTV_NO_START="1", SMTV_LANG="en")
    cases.append(run_case("c0", "PowerShell's language mode under the policy",
                          ["powershell", "-NoProfile", "-Command", "$ExecutionContext.SessionState.LanguageMode"], 60,
                          ok=lambda r: True, env=env))
    script = repo / "install" / "install.ps1"
    cases.append(run_case("c1", "the one-line install (install.ps1 of this branch, as `irm | iex` runs it)",
                          ["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass", "-Command",
                           f"Get-Content -Raw -LiteralPath '{script}' | Invoke-Expression"], 1800, env=env))
    found = uv_python(env)
    if not found:
        cases.append({"name": "c2", "what": "SMTV from install.ps1", "ok": False, "blocked": False, "blocked_by": [],
                      "events": [], "command": "", "output": "uv's tool folder has no smtv: the install did not finish"})
        return cases
    python, pythonw = found
    cases.append(run_case("c2", "`python -m smtv doctor`", [python, "-m", "smtv", "doctor"], 600, env=env,
                          ok=lambda r: "ffmpeg" in r.stdout))
    cases.append(run_case("c3", "the heavy libraries and the window's bridge (pythonnet, WinForms, WebView2) load",
                          [python, "-c", PROBE], 600, env=env, ok=lambda r: "loaded" in r.stdout))
    cases.append(serve_case(python, env))
    cases.append(window_case(pythonw, env))
    return cases


# --- signatures ------------------------------------------------------------------------------------------------------

def signatures(dirs: list[str]) -> list[dict]:
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass", "-Command",
                        "& {" + SIGNATURES_PS + "}", *dirs], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=windows_env())
    if r.returncode != 0:
        raise SystemExit(f"Get-AuthenticodeSignature failed: {r.stderr.strip()[-1500:]}")
    rows = json.loads(r.stdout or "[]")
    return rows if isinstance(rows, list) else [rows]


def common_name(subject: str) -> str:
    for part in subject.split(","):
        part = part.strip()
        if part.startswith("CN="):
            return part[3:].strip('"')
    return subject or "-"


def package_of(rel: str) -> str:
    """Where an unsigned file belongs: the package under site-packages, else the top folder."""
    parts = rel.replace("\\", "/").split("/")
    if "site-packages" in parts:
        i = parts.index("site-packages")
        return parts[i + 1] if i + 1 < len(parts) else "site-packages"
    return parts[0] if len(parts) > 1 else "(top folder)"


def summarize_signatures(rows: list[dict]) -> str:
    lines = []
    for root in dict.fromkeys(r["root"] for r in rows):
        mine = [r for r in rows if r["root"] == root]
        lines += [f"#### {Path(root).name} ({root}): {len(mine)} files (.exe, .dll, .pyd)", "",
                  "| Status | Signed by | Files |", "|---|---|---|"]
        counts: dict[tuple[str, str], int] = {}
        for r in mine:
            key = (r["status"], common_name(r["signer"]) if r["signer"] else "-")
            counts[key] = counts.get(key, 0) + 1
        lines += [f"| {s} | {who} | {n} |" for (s, who), n in sorted(counts.items(), key=lambda kv: -kv[1])]
        lines += ["", "| Key file | Status | Signed by |", "|---|---|---|"]
        for name in KEY_FILES:
            for r in mine:
                if Path(r["path"]).name.lower() == name.lower():
                    rel = os.path.relpath(r["path"], root)
                    lines.append(f"| {rel} | {r['status']} | {common_name(r['signer']) if r['signer'] else '-'} |")
        unsigned: dict[str, int] = {}
        for r in mine:
            if r["status"] != "Valid":
                pkg = package_of(os.path.relpath(r["path"], root))
                unsigned[pkg] = unsigned.get(pkg, 0) + 1
        lines += ["", "Not validly signed, by package: " +
                  (", ".join(f"{k} {v}" for k, v in sorted(unsigned.items(), key=lambda kv: -kv[1])) or "none"), ""]
    return "\n".join(lines)


# --- the report ------------------------------------------------------------------------------------------------------

def verdict(case: dict) -> str:
    if case["name"] == "0":
        return "blocked: the policy is on" if case["blocked"] else "NOT blocked: the policy is not enforced"
    if case.get("ok"):
        return "works" + (" (some files blocked, see below)" if case["blocked"] else "")
    return "BLOCKED" if case["blocked"] else "failed (not by the policy)"


def report(cases: list[dict], policy: str, sig_summary: str) -> str:
    lines = ["## SMTV under a policy like Smart App Control", "", f"Policy: {policy or 'unknown'}", "",
             "| | What | Result | Blocked files |", "|---|---|---|---|"]
    for c in cases:
        files = ", ".join(Path(f).name for f in c["blocked_by"][:6]) + (" …" if len(c["blocked_by"]) > 6 else "")
        lines.append(f"| {c['name']} | {c['what']} | {verdict(c)} | {files or '-'} |")
    for c in cases:
        lines += ["", f"### {c['name']}: {c['what']}", "", f"`{c['command']}` → exit {c.get('exit')}", "", "```",
                  (c.get("output") or "").strip()[-2500:], "```"]
        shown = [e for e in c["events"] if e["id"] in BLOCKED_IDS | AUDIT_IDS][:40]
        if shown:
            lines += ["", "| Event | File | Process | Policy |", "|---|---|---|---|"]
            lines += [f"| {e['id']} | {e['file']} | {e['process']} | {e['policy']} |" for e in shown]
    if sig_summary:
        lines += ["", "## Signatures (before the policy)", "", sig_summary]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # a Windows runner's console is cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("signatures", help="before the policy: the Authenticode status of every .exe, .dll and .pyd")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("dirs", nargs="+")
    r = sub.add_parser("run", help="under the policy: every case, the report")
    r.add_argument("--work", type=Path, required=True, help="the release's files, the ZIP unpacked, control.exe")
    r.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args(argv)
    if a.cmd == "signatures":
        rows = signatures([d for d in a.dirs if Path(d).is_dir()])
        a.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(summarize_signatures(rows))
        return 0
    cases = run_all(a.work, a.repo.resolve())
    sig = a.work / "signatures.json"
    summary = summarize_signatures(json.loads(sig.read_text(encoding="utf-8"))) if sig.is_file() else ""
    policy = (a.work / "policy-name.txt").read_text(encoding="utf-8-sig").strip() if (a.work / "policy-name.txt").is_file() else ""
    text = report(cases, policy, summary)
    (a.work / "report.md").write_text(text, encoding="utf-8")
    (a.work / "report.json").write_text(json.dumps(cases, indent=1), encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0 if cases and cases[0]["blocked"] else 1     # without a working policy the rest means nothing


if __name__ == "__main__":
    raise SystemExit(main())
