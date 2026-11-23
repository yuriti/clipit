"""What one recording looks like, decided once for all its clips and its recap (B12): where the streamer's webcam is
and which ad slots to blur. Kept in the job as scene.json.

Measured 23.11 (a 26-minute recording, 3 clips and a recap): the webcam took 12 model calls and the ads 6, while both
stay the same through a stream. Now:

- the webcam is looked for on this computer, on each clip's frames (smtv_core.render.look); a webcam found once is
  that webcam again on the next clip when the streamer's face is in it. The model is asked only when the frames leave
  a doubt (no face, two candidates, a box that does not look like a webcam), and its answer is kept for the next clips;
- the ad slots: ONE question per recording, on five frames spread over it — the banner prompt is made for exactly that
  («blur regions for ONE entire streamer video»). Looking for still overlays on this computer was tried first and
  missed the rotating sponsor slots (3 of 3 on one stream): they are not on every frame.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Callable

from smtv_core.render import faces as face_model
from smtv_core.render import look as looking

SCENE = "scene.json"
RULE = 1          # a scene.json of another rule is looked at again
NONE_AGREED = 2   # «no webcam» is taken for the whole recording only after this many model answers said so
AD_FRAMES_KEPT = 4   # an ad answer on fewer frames of the recording serves its clip but is not kept for the others


class Scene:
    """The scene of one job, shared by the threads of one run."""

    def __init__(self, job: Path | None):
        self.path = job / SCENE if job is not None else None
        self.lock = threading.RLock()
        data = self._read()
        self.cameras: list[dict] = [c for c in data.get("cameras") or [] if isinstance(c, dict) and isinstance(c.get("camera"), dict)]
        self.none: dict | None = data.get("none") if isinstance(data.get("none"), dict) else None
        self.ads: dict | None = data.get("ads") if isinstance(data.get("ads"), dict) else None

    def _read(self) -> dict:
        if self.path is None:
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) and data.get("rule") == RULE else {}

    def save(self) -> None:
        if self.path is None:
            return
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_text(json.dumps({"rule": RULE, "cameras": self.cameras, "none": self.none, "ads": self.ads},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            tmp.unlink(missing_ok=True)       # kept in memory for this run; the next run looks again

    # --- the webcam ------------------------------------------------------------------------------------------

    def look(self, shots: list[Path]) -> looking.Look:
        """The webcam on these frames, by this computer alone; «unsure» when the model must be asked (also when the
        face detector cannot run here)."""
        with self.lock:
            known = [c["camera"] for c in self.cameras]
            faceless = [c["camera"] for c in self.cameras if c.get("faceless")]
        try:
            found = looking.look([looking.bgr(Path(p)) for p in shots], known, faceless)
        except face_model.FacesUnavailable as e:
            return looking.Look("unsure", reason=f"faces cannot be looked for here: {e}"[:300])
        except Exception as e:  # noqa: BLE001 — a frame that cannot be read: the model decides, as before B12
            return looking.Look("unsure", reason=f"the frames could not be looked at: {type(e).__name__}: {e}"[:300])
        if (found.kind == "unsure" and self.none is not None and self.none.get("answers", 1) >= NONE_AGREED and not found.candidates
                and not self.cameras):            # a webcam found since then is never overruled by «no webcam»
            # the model found no webcam box on this recording before, and nothing here looks like one either
            return looking.Look("full" if self.none.get("full") else "none", face=found.face,
                                reason=f"no webcam on this recording ({self.none.get('how', 'model')})", faces=found.faces, known=True)
        return found

    def remember(self, found: looking.Look, camera: dict | None, how: str, *, full: bool = False) -> None:
        """Keeps what the frames (`found`) or the model (`how` starts with «model») decided, for the next clips."""
        with self.lock:
            if camera is not None:
                if not any(c["camera"] == camera for c in self.cameras):
                    self.cameras.append({"camera": camera, "how": how, "faceless": bool(found.faces) and not any(found.faces)})
            elif not self.cameras and (self.none is None or self.none.get("answers", 1) < NONE_AGREED):
                # one answer may come from frames that hide the webcam (an avatar, a dark camera): it decides its clip,
                # and the recording only when another answer agrees
                before = self.none or {}
                agreed = before.get("full") == full and bool(before)
                self.none = {"how": how, "full": full, "answers": before.get("answers", 1) + 1 if agreed else 1}
            else:
                return
            self.save()

    # --- the ads ---------------------------------------------------------------------------------------------

    def ad_boxes(self, find: Callable[[list[Path]], tuple[list, str]], frames: Callable[[], list[Path]]) -> tuple[list, str]:
        """(boxes on the 1920x1080 source, how they were found) for the whole recording: asked once, kept in
        scene.json; an unusable answer is not kept, so the next clip (or the next run) asks again."""
        with self.lock:
            if self.ads is not None:
                return [tuple(b) for b in self.ads.get("boxes") or []], f"{self.ads.get('by', 'model')}: the recording"
            try:
                shots = frames()
            except Exception as e:  # noqa: BLE001 — no frames, no answer: nothing is blurred and the next clip asks again
                return [], f"none: frames of the recording: {type(e).__name__}: {e}"[:300]
            if not shots:
                return [], "none: no frames of the recording"
            boxes, by = find(shots)
            if by.startswith("none:") or len(set(map(str, shots))) < AD_FRAMES_KEPT:
                return boxes, by                  # no answer, or one on too few frames to stand for the whole recording
            self.ads = {"boxes": [list(b) for b in boxes], "by": by, "frames": len(shots)}
            self.save()
            return boxes, by

