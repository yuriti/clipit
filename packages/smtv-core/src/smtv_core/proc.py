"""Running ffmpeg, ffprobe and yt-dlp with a time limit.

A program that hangs (a stalled download, a broken file ffmpeg keeps reading) must not hold the whole job forever: after
`timeout_s` it is stopped together with everything it started (yt-dlp starts ffmpeg) and `TimedOut` names what hung.
"""
from __future__ import annotations

import os
import signal
import subprocess


class TimedOut(RuntimeError):
    pass


def limit(duration_s: float, *, floor_s: float = 300.0, per_s: float = 10.0) -> float:
    """A time limit for work on `duration_s` seconds of media: `per_s` seconds per second of media, at least `floor_s`."""
    return max(floor_s, per_s * max(0.0, float(duration_s or 0)))


def _kill(p: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(p.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        p.kill()
    except OSError:
        pass


def hidden() -> dict:
    """Popen keywords that keep a console program from opening a black window on Windows (SMTV runs under pythonw)."""
    if os.name == "posix":
        return {}
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}


def group() -> dict:
    """Popen keywords that put a program and everything it starts into one group `_kill` can stop at once.

    Windows also gets no console window: every program SMTV starts is a console one (ffmpeg, yt-dlp, codex.cmd).
    """
    if os.name == "posix":
        return {"start_new_session": True}
    return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200) | hidden()["creationflags"]}


def run(cmd: list[str], timeout_s: float, *, what: str = "", text: bool = True, input: str | bytes | None = None,
        env: dict | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    """subprocess.run(cmd, capture_output=True) with a hard time limit on the program and its children.

    Text goes both ways in UTF-8 whatever the system code page (a Russian Windows would otherwise send cp1251 to a
    program that reads UTF-8); `input` is written to the program's stdin.
    """
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL if input is None else subprocess.PIPE, text=text, env=env, cwd=cwd,
                         **({"encoding": "utf-8", "errors": "replace"} if text else {}), **group())
    try:
        out, err = p.communicate(input=input, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill(p)
        try:
            p.communicate(timeout=10)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass
        raise TimedOut(f"{what or os.path.basename(cmd[0])} did not finish in {round(timeout_s)} s and was stopped") from None
    except BaseException:
        _kill(p)
        try:
            p.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            pass
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def exit_on_terminate() -> None:
    """In a job process: SIGTERM («Остановить», quitting SMTV) becomes SystemExit.

    Without it Python dies on the signal without running `finally`, and the ffmpeg or yt-dlp `run` started in its own
    session never hears about it: it keeps writing into the job folder. With it `run` stops its program tree first.
    """
    if os.name != "posix":
        return

    def _exit(signum, frame):  # noqa: ARG001
        raise SystemExit(128 + signum)

    try:
        signal.signal(signal.SIGTERM, _exit)
    except ValueError:      # not the main thread: nothing to install
        pass
