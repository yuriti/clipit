"""Faces on a frame, found on this computer: YuNet (a 230 KB face detector) through onnxruntime, which SMTV already has
for speech recognition. No model call and no new package (B12): the layout asks a model only when the faces leave a
doubt.

The model file `models/yunet.onnx` is `face_detection_yunet_2026may.onnx` of the OpenCV model zoo
(https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet, MIT License, `models/LICENSE-YuNet.txt`):
the 2023mar network re-exported with any input size. The decoding below follows OpenCV's own YuNet post-processing
(modules/objdetect/src/face_detect.cpp, Apache-2.0): per stride 8, 16 and 32 a score sqrt(cls · obj), a box centred at
(column + dx, row + dy) · stride of size exp(dw), exp(dh) · stride; then non-maximum suppression.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL = Path(__file__).with_name("models") / "yunet.onnx"
STRIDES = (8, 16, 32)
SCORE = 0.7                 # a face below this is not counted (OpenCV's demos use 0.9; a webcam face is small and soft)
OVERLAP = 0.3               # non-maximum suppression: boxes overlapping more than this are one face

_session = None
_session_lock = threading.Lock()


class FacesUnavailable(RuntimeError):
    """The detector cannot run here (onnxruntime or the model file missing): the layout asks the model instead."""


@dataclass(frozen=True)
class Face:
    x: float                # fractions of the frame
    y: float
    width: float
    height: float
    score: float

    @property
    def centre(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    def as_dict(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "width": round(self.width, 4), "height": round(self.height, 4)}


def _model():
    global _session
    with _session_lock:
        if _session is None:
            try:
                import onnxruntime as ort
            except ImportError as e:
                raise FacesUnavailable(f"onnxruntime is not installed: {e}") from e
            if not MODEL.is_file():
                raise FacesUnavailable(f"the face model is missing: {MODEL.name}")
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2            # a few frames a clip: no need to take every core from the encode
            options.log_severity_level = 3
            try:
                _session = ort.InferenceSession(str(MODEL), options, providers=["CPUExecutionProvider"])
            except Exception as e:  # noqa: BLE001 — a broken model file or runtime: no faces, the model decides the layout
                raise FacesUnavailable(f"the face model does not load: {type(e).__name__}: {e}"[:300]) from e
        return _session


def _iou(a: tuple, b: tuple) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)


def decode(outputs: dict[str, np.ndarray], padded_w: int, score: float = SCORE) -> list[tuple]:
    """(x, y, width, height, score) in pixels of the padded input, strongest first, overlaps removed."""
    found = []
    for stride in STRIDES:
        cols = padded_w // stride
        cls = np.clip(outputs[f"cls_{stride}"][0, :, 0], 0, 1)
        obj = np.clip(outputs[f"obj_{stride}"][0, :, 0], 0, 1)
        scores = np.sqrt(cls * obj)
        boxes = outputs[f"bbox_{stride}"][0]
        for i in np.nonzero(scores >= score)[0]:
            row, col = divmod(int(i), cols)
            cx, cy = (col + boxes[i, 0]) * stride, (row + boxes[i, 1]) * stride
            w, h = float(np.exp(boxes[i, 2])) * stride, float(np.exp(boxes[i, 3])) * stride
            found.append((float(cx - w / 2), float(cy - h / 2), w, h, float(scores[i])))
    found.sort(key=lambda f: -f[4])
    kept: list[tuple] = []
    for f in found:
        if all(_iou(f, k) < OVERLAP for k in kept):
            kept.append(f)
    return kept


def detect(image: np.ndarray, score: float = SCORE) -> list[Face]:
    """Faces on a BGR image (height × width × 3, uint8), as fractions of it, strongest first. Raises FacesUnavailable."""
    session = _model()
    h, w = image.shape[:2]
    ph, pw = -(-h // 32) * 32, -(-w // 32) * 32          # the network's strides need a multiple of 32: padded below and right
    padded = np.zeros((ph, pw, 3), np.float32)
    padded[:h, :w] = image
    names = [o.name for o in session.get_outputs()]
    outputs = dict(zip(names, session.run(None, {session.get_inputs()[0].name: padded.transpose(2, 0, 1)[None]})))
    faces = []
    for x, y, fw, fh, s in decode(outputs, pw, score):
        x0, y0 = max(0.0, x), max(0.0, y)
        x1, y1 = min(float(w), x + fw), min(float(h), y + fh)
        if x1 - x0 >= 2 and y1 - y0 >= 2:
            faces.append(Face(x0 / w, y0 / h, (x1 - x0) / w, (y1 - y0) / h, s))
    return faces
