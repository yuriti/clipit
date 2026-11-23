"""SMTV's updater: a separate process that changes SMTV while SMTV is not running (stage 8).

Started by the running SMTV (`updates.start_updater`) with the Python that SMTV's environment was made from, outside
that environment, from a copy of this file in `<SMTV home>/run/`: the installer replaces the environment, and on Windows
the files of a running program are locked. So this file uses the standard library only (a test checks it).

1. Waits for the SMTV that started it to quit (it quits right after starting this).
2. Runs the plan's steps (`uv tool install --reinstall "smtv[...]==X" ...` or `pip install --upgrade ...`).
3. Starts SMTV again and waits until it answers on its port with the expected version and tools.
4. If a step failed or SMTV did not come up: asks that SMTV (if any) to quit, puts back the versions written down before
   (the plan's rollback steps), starts SMTV again and checks it the same way. If even that fails, a system dialog says
   so and where the log is.

The result goes to the status file the next SMTV reads (`done`, `rolled_back`, `failed`); the output to the log.
"""
from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import time

HELLO_TIMEOUT_S = 180.0
QUIT_WAIT_S = 120.0
LATE_QUIT_S = 1800.0      # the old SMTV took longer to quit: no change, but it is started again once it is gone
STEP_TIMEOUT_S = 1800.0
NO_WINDOW = 0x08000000    # CREATE_NO_WINDOW


def log(msg: str) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def write_status(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # type: ignore[attr-defined]
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))  # type: ignore[attr-defined]
        ctypes.windll.kernel32.CloseHandle(h)  # type: ignore[attr-defined]
        return code.value == 259    # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_gone(pid: int, timeout: float, sleep=time.sleep) -> bool:
    end = time.monotonic() + timeout
    while pid_alive(pid):
        if time.monotonic() > end:
            return False
        sleep(0.3)
    return True


def hello(port: int) -> dict | None:
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/hello", headers={"Host": f"127.0.0.1:{port}"})
        r = conn.getresponse()
        data = json.loads(r.read(100_000) or b"{}") if r.status == 200 else None
        conn.close()
    except (OSError, ValueError, http.client.HTTPException):
        return None
    return data if isinstance(data, dict) and data.get("app") == "smtv" else None


def matches(answer: dict | None, expect: dict) -> bool:
    """The expected version and tools. Only SMTV's own tools are compared (`known`): a third-party plugin the person
    installed is in /api/hello too, and it is not a failed update."""
    if not answer or answer.get("version") != expect.get("version"):
        return False
    tools = set(answer.get("tools") or [])
    if expect.get("known") is not None:
        tools &= set(expect["known"])
    return sorted(tools) == sorted(expect.get("tools") or [])


def wait_hello(port: int, expect: dict, timeout: float, sleep=time.sleep, proc=None) -> dict | None:
    """The SMTV started again answers with the expected version and tools; None when it never does in time, or when
    the process started for it (`proc`, if it is SMTV itself and not a launcher like `open`) ended without answering."""
    end, last = time.monotonic() + timeout, None
    while time.monotonic() < end:
        last = hello(port)
        if matches(last, expect):
            return last
        if proc is not None and proc.poll() is not None and not hello(port):
            log(f"SMTV ended at its start with exit code {proc.returncode}")
            return None
        sleep(1.0)
    log(f"SMTV did not come up as expected {expect}: last answer {last}")
    return None


def ask_quit(home: str, port: int) -> None:
    """A wrong SMTV answers on the port (an unexpected version): ask it to quit with its own session token."""
    try:
        with open(os.path.join(home, "run", "session.json"), encoding="utf-8") as f:
            session = json.load(f)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/api/quit", body=b"{}", headers={"Host": f"127.0.0.1:{port}", "X-SMTV-Token": session["token"],
                                                             "Content-Type": "application/json"})
        conn.getresponse().read()
        conn.close()
        wait_gone(int(session.get("pid") or 0), 30)
    except (OSError, ValueError, KeyError, http.client.HTTPException):
        pass


def run_steps(steps: list[list[str]], runner=subprocess.run) -> bool:
    for argv in steps:
        log("run: " + " ".join(argv))
        kwargs = {"creationflags": NO_WINDOW} if sys.platform == "win32" else {}   # uv.exe is a console program
        try:
            r = runner(argv, stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=subprocess.STDOUT, timeout=STEP_TIMEOUT_S, **kwargs)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(f"failed: {type(e).__name__}: {e}")
            return False
        if r.returncode != 0:
            log(f"failed with exit code {r.returncode}")
            return False
    return True


def launch(argv: list[str], popen=subprocess.Popen):
    """Starts SMTV; returns its process when it is SMTV itself (so an early end is seen at once), None for a launcher
    that exits right away by design (`open SMTV.app` on a Mac)."""
    log("start: " + " ".join(argv))
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    try:
        p = popen(argv, **kwargs)
    except OSError as e:
        log(f"could not start SMTV: {e}")
        return None
    return None if os.path.basename(argv[0]) == "open" else p


def stop(proc) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(15)
    except (OSError, subprocess.TimeoutExpired):
        try:
            proc.kill()
            proc.wait(5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def alert(text: str) -> None:
    """The last resort: SMTV could not be started even with the old versions. A dialog, since no window is left."""
    log(text)
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", "on run argv", "-e", 'display alert "SMTV" message (item 1 of argv) as critical',
                            "-e", "end run", text], capture_output=True, timeout=600)
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "SMTV", 0x10)  # type: ignore[attr-defined]
        else:
            subprocess.run(["notify-send", "SMTV", text], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pass


def update(plan: dict, runner=subprocess.run, popen=subprocess.Popen, sleep=time.sleep) -> str:
    """Does the plan; returns the final state: done, rolled_back or failed."""
    status_path, port = plan["status"], int(plan["port"])
    timeout = float(plan.get("timeout_s") or HELLO_TIMEOUT_S)
    status = {"action": plan["action"], "from": plan["previous"], "to": plan["expect"], "pid": os.getpid(),
              "started": time.time(), "log": plan["log"]}

    def say(state: str, **extra) -> None:
        status.update(state=state, **extra)
        write_status(status_path, status)
        log(f"state: {state}")

    say("waiting")
    if not wait_gone(int(plan["wait_pid"]), QUIT_WAIT_S, sleep):
        # Nothing is installed over a running SMTV. It still quits, later: start it again then, unchanged.
        say("failed", finished=time.time(), why="SMTV did not quit")
        if wait_gone(int(plan["wait_pid"]), LATE_QUIT_S, sleep) and not hello(port):
            launch(plan["relaunch"], popen)
        return "failed"
    say("installing")
    ok = run_steps(plan["steps"], runner)
    proc = None
    if ok:
        say("starting")
        proc = launch(plan["relaunch"], popen)
        ok = wait_hello(port, plan["expect"], timeout, sleep, proc) is not None
    if ok:
        say("done", finished=time.time())
        return "done"
    stop(proc)                         # the new SMTV, if it still starts or runs: never two of them
    if hello(port):
        ask_quit(plan["home"], port)
    say("rolling_back")
    # from uv's cache first: the update may have failed for want of network, and then a rollback over the network fails too
    back = bool(plan.get("rollback_offline")) and run_steps(plan["rollback_offline"], runner)
    back = back or run_steps(plan["rollback"], runner)
    proc = launch(plan["relaunch"], popen)
    # SMTV is asked even when the rollback failed: a failed install usually leaves the environment as it was, and then
    # the previous version simply starts. That is «nothing changed», not «SMTV is broken».
    if wait_hello(port, plan["previous"], timeout, sleep, proc) is not None:
        say("rolled_back", finished=time.time(), **({} if back else {"why": "the update did not install; the previous version stayed"}))
        return "rolled_back"
    say("failed", finished=time.time())
    alert(f"SMTV could not be updated and the previous version did not start either. What happened: {plan['log']}")
    return "failed"


def main(argv: list[str]) -> int:
    with open(argv[0], encoding="utf-8") as f:
        plan = json.load(f)
    log(f"--- SMTV updater: {plan['action']} {plan['previous']} -> {plan['expect']}")
    try:
        state = update(plan)
    except Exception as e:  # noqa: BLE001 — whatever happened, SMTV must come back and the person must know
        log(f"the updater broke: {type(e).__name__}: {e}")
        try:
            write_status(plan["status"], {"state": "failed", "action": plan["action"], "from": plan["previous"], "to": plan["expect"],
                                          "pid": os.getpid(), "finished": time.time(), "log": plan["log"], "why": f"{type(e).__name__}: {e}"})
        except OSError:
            pass
        if not hello(int(plan["port"])):
            launch(plan["relaunch"])
        alert(f"SMTV could not be updated. What happened: {plan['log']}")
        return 1
    return 0 if state == "done" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
