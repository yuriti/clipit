"""What runs now (notifications, the Dock badge) and the idle shutdown, without real windows."""
from __future__ import annotations

import http.client
import json
import threading
import time

import pytest

from smtv import activity, desktop, serve
from smtv.activity import IdleWatch, JobProgress, Tracker
from smtv_core.events import Journal


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def ev(kind, t, **data):
    return {"type": kind, "t": t, "data": data}


# --- progress from the journal ---------------------------------------------------------------------------------------

def test_job_progress_counts_clips_of_the_montage_and_estimates_the_rest():
    p = JobProgress("vodcut", "v1", started=0)
    p.feed(ev("stage", 10, name="speech"))
    assert p.stage == "speech" and p.eta_s() is None
    p.feed(ev("stage", 100, name="render", clips=12))
    p.feed(ev("clip_ready", 160, clip="clip01", file="clips/clip01.mp4"))
    p.feed(ev("clip_failed", 220, clip="clip02", error="x"))
    p.feed(ev("clip_ready", 280, clip="clip03", file="clips/clip03.mp4"))
    assert (p.clips_total, p.clips_ready, p.clips_failed) == (12, 2, 1)
    assert p.eta_s() == pytest.approx(60 * 9)            # 60 s per clip so far, 9 clips left


def test_a_rerun_of_the_montage_starts_counting_again():
    p = JobProgress("vodcut", "v1", started=0)
    p.feed(ev("stage", 1, name="render", clips=3))
    p.feed(ev("clip_ready", 2, clip="clip01", file="a"))
    p.feed(ev("stage", 5, name="render", clips=3))
    assert p.clips_ready == 0


class FakeRun:
    def __init__(self, tool, folder, first=0):
        self.tool, self.folder, self.first, self.started = tool, folder, first, time.time()
        self.finished = threading.Event()

    @property
    def job(self):
        return self.folder.name


class FakeRunner:
    def __init__(self):
        self.runs = {}


def test_tracker_reads_running_jobs_from_their_journals(tmp_path):
    runner = FakeRunner()
    folders = []
    for name, clips in (("a", 4), ("b", 8)):
        folder = tmp_path / name
        with Journal(folder, tool="vodcut", subscribers=[]) as j:
            j.emit("stage", name="render", clips=clips)
            j.emit("clip_ready", clip="clip01", file="clips/clip01.mp4")
        runner.runs[("vodcut", name)] = FakeRun("vodcut", folder)
        folders.append(folder)
    tracker = Tracker(runner)
    act = tracker.snapshot()
    assert (act["running"], act["clips_ready"], act["clips_total"]) == (2, 2, 12)
    with Journal(folders[0], tool="vodcut", subscribers=[]) as j:      # read further, not again
        j.emit("clip_ready", clip="clip02", file="clips/clip02.mp4")
    assert tracker.snapshot()["clips_ready"] == 3
    runner.runs[("vodcut", "b")].finished.set()
    act = tracker.snapshot()
    assert act["running"] == 1 and act["clips_total"] == 4


def test_notifications_only_for_done_and_failed():
    assert activity.finished_text("done", "Стрим", 6, "ru") == ("SMTV: готово", "Стрим — клипов: 6")
    assert activity.finished_text("failed", "Stream", 0, "en")[0] == "SMTV: failed"
    assert activity.finished_text("cancelled", "x", 0, "ru") is None      # the person stopped it themselves


# --- idle shutdown ---------------------------------------------------------------------------------------------------

class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.mark.parametrize("busy,keep", [(True, False), (False, True)])
def test_idle_never_stops_while_busy_or_kept(busy, keep):
    clock = Clock()
    w = IdleWatch(300, busy=lambda: busy, keep=lambda: keep, clock=clock)
    for _ in range(10):
        assert not w.should_stop()
        clock.now += 100


def test_idle_stops_after_the_quiet_time_and_any_activity_resets_it():
    clock, state = Clock(), {"busy": False}
    w = IdleWatch(300, busy=lambda: state["busy"], keep=lambda: False, clock=clock)
    assert not w.should_stop()
    clock.now = 200
    state["busy"] = True                        # a page opened for a moment
    assert not w.should_stop()
    state["busy"] = False
    clock.now = 250
    assert not w.should_stop()
    clock.now = 549
    assert not w.should_stop()
    clock.now = 550
    assert w.should_stop()


# --- the watcher: tray look, notifications, idle, all from activity ---------------------------------------------------

class FakeApp:
    def __init__(self):
        self.acts, self.infos = [], {}
        self.stopping = threading.Event()

    def activity(self):
        return self.acts.pop(0) if len(self.acts) > 1 else self.acts[0]

    def job(self, tool, job):
        return self.infos[(tool, job)]


def act(jobs, viewers=0):
    a = activity.summary(jobs)
    a["viewers"] = viewers
    return a


def job(name, ready=0, total=4):
    return {"tool": "vodcut", "job": name, "started": 1, "stage": "render", "clips_ready": ready, "clips_failed": 0,
            "clips_total": total, "eta_s": None}


def test_watcher_notifies_when_jobs_end_and_counts_them_on_the_badge():
    app, told, badge = FakeApp(), [], []
    w = desktop.Watcher(app, lambda: None, "ru", notify=lambda *m: told.append(m), badge=badge.append)
    app.acts = [act([job("a", 1), job("b", 0)], viewers=1), act([job("a", 2), job("b", 0)]), act([job("b", 1)]), act([])]
    app.infos = {("vodcut", "a"): {"status": "done", "title": "Стрим А", "clips": 4},
                 ("vodcut", "b"): {"status": "failed", "title": "Стрим Б", "clips": 0}}
    stops = [w.tick() for _ in range(4)]
    assert badge == [2, 1, 0]                                    # set only when the count changes
    assert told == [("SMTV: готово", "Стрим А — клипов: 4"), ("SMTV: ошибка", "Стрим Б — подробности на странице")]
    assert stops == [False] * 4                                  # SMTV's window: never stops by itself


def test_watcher_skips_cancelled_jobs():
    app, told = FakeApp(), []
    w = desktop.Watcher(app, lambda: None, "en", notify=lambda *m: told.append(m))
    app.acts = [act([job("a")]), act([])]
    app.infos = {("vodcut", "a"): {"status": "cancelled", "title": "x", "clips": 0}}
    w.tick(), w.tick()
    assert told == []


def test_in_the_browser_smtv_stops_when_idle_but_not_with_a_page_or_a_job():
    clock = Clock()
    app = FakeApp()
    w = desktop.Watcher(app, lambda: None, "en", idle_s=300, notify=lambda *m: None, clock=clock)
    app.acts = [act([], viewers=1)]
    assert not w.tick()
    clock.now = 1000
    assert not w.tick()                                     # a page is open
    app.acts = [act([job("a")])]
    clock.now = 2000
    assert not w.tick()                                     # a job runs, no page
    app.acts = [act([])]
    app.infos = {("vodcut", "a"): {"status": "done", "title": "", "clips": 1}}
    clock.now = 3000
    assert not w.tick()
    clock.now = 3299
    assert not w.tick()
    clock.now = 3300
    assert w.tick()


def test_watcher_run_stops_the_server_on_idle():
    app, stopped = FakeApp(), threading.Event()
    app.acts = [act([])]
    w = desktop.Watcher(app, stopped.set, "en", idle_s=0, notify=lambda *m: None)
    threading.Thread(target=w.run, daemon=True).start()
    assert stopped.wait(5)


@pytest.fixture
def server():
    app = serve.App([], [])
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield srv.server_address[1], app
    app.stopping.set()
    srv.shutdown()
    srv.server_close()


def req(port, method, path, body=None, token=None, app=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Host": f"127.0.0.1:{port}"}
    if token:
        headers["X-SMTV-Token"] = token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    res = conn.getresponse()
    out = res.status, json.loads(res.read() or b"{}")
    conn.close()
    return out


def test_a_page_asking_for_activity_counts_as_open_until_it_goes_quiet(server):
    port, app = server
    clock = {"now": 1000.0}
    app.clock = lambda: clock["now"]
    status, body = req(port, "GET", "/api/activity?page=tab0000001", token=app.token)
    assert status == 200 and body["running"] == 0 and body["viewers"] == 1
    req(port, "GET", "/api/activity?page=tab0000002", token=app.token)
    req(port, "GET", "/api/activity?page=tab0000001", token=app.token)             # the same page again: still two pages
    assert app.viewers == 2
    clock["now"] += serve.PAGE_TTL_S - 1                           # a hidden tab is woken about once a minute
    assert app.viewers == 2
    clock["now"] += 2                                              # the windows closed
    assert app.viewers == 0
    req(port, "GET", "/api/activity?page=../../etc", token=app.token)               # a bad id is ignored
    assert app.viewers == 0


def test_activity_holds_no_connection_open(server):
    """A browser allows six connections per site across all tabs: the page must not hold one per tab for this."""
    port, app = server
    assert req(port, "GET", "/api/activity/events", token=app.token)[0] == 404




def test_notifications_speak_the_language_chosen_on_the_page(server):
    port, app = server
    req(port, "GET", "/api/activity?page=tab0000001&lang=ru", token=app.token)
    assert app.lang == "ru"
    req(port, "GET", "/api/activity?page=tab0000001&lang=xx", token=app.token)       # only known languages
    assert app.lang == "ru"
    fake, told = FakeApp(), []
    fake.lang = "ru"
    w = desktop.Watcher(fake, lambda: None, "en", notify=lambda *m: told.append(m))
    fake.acts = [act([job("a")]), act([])]
    fake.infos = {("vodcut", "a"): {"status": "done", "title": "Стрим", "clips": 2}}
    w.tick(), w.tick()
    assert told == [("SMTV: готово", "Стрим — клипов: 2")]


def test_mac_notifications_fall_back_without_permission():
    from smtv import window
    window._notifications["granted"] = False
    assert window.mac_notify("SMTV: done", "x") is False             # then osascript sends it
