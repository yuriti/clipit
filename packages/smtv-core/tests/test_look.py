"""B12: the webcam found on the frames on this computer (faces.py, look.py) and the layout made from it.

The frames are drawn here: a «game» that changes from frame to frame, a webcam box with a still «room» and a drawn face
(no real person in a fixture). YuNet finds a drawn face like this with a score of 0.75–0.88."""
from __future__ import annotations

import numpy as np
import pytest

from smtv_core.render import camera, faces, look
from smtv_core.render.layout import SLOTS, best_split, from_frames

H, W = look.WORK_H, look.WORK_W
YY, XX = np.mgrid[0:H, 0:W]


def draw_face(img: np.ndarray, cx: float, cy: float, r: float) -> None:
    img[((XX - cx) / r) ** 2 + ((YY - cy) / (1.3 * r)) ** 2 <= 1] = (150, 170, 215)
    hair = (((XX - cx) / (1.05 * r)) ** 2 + ((YY - (cy - 0.55 * r)) / (0.8 * r)) ** 2 <= 1) & (YY < cy - 0.45 * r)
    img[hair] = (30, 30, 40)
    for ex in (-0.38, 0.38):
        img[((XX - (cx + ex * r)) / (0.2 * r)) ** 2 + ((YY - (cy - 0.15 * r)) / (0.12 * r)) ** 2 <= 1] = (250, 250, 250)
        img[((XX - (cx + ex * r)) / (0.09 * r)) ** 2 + ((YY - (cy - 0.15 * r)) / (0.09 * r)) ** 2 <= 1] = (40, 30, 20)
        img[(abs(YY - (cy - 0.38 * r)) < 0.04 * r) & (abs(XX - (cx + ex * r)) < 0.22 * r)] = (40, 40, 50)
    img[(abs(XX - cx) < 0.06 * r) & (YY > cy - 0.05 * r) & (YY < cy + 0.3 * r)] = (120, 140, 190)
    img[((XX - cx) / (0.35 * r)) ** 2 + ((YY - (cy + 0.55 * r)) / (0.1 * r)) ** 2 <= 1] = (60, 60, 160)


def game(rng, i: int) -> np.ndarray:
    """A picture that changes a lot from one frame to the next: coarse random blocks."""
    blocks = rng.integers(0, 255, (H // 30 + 1, W // 30 + 1, 3)).astype(np.uint8)
    return np.kron(blocks, np.ones((30, 30, 1), np.uint8))[:H, :W].copy()


def room(rng) -> np.ndarray:
    """A still room: soft blotches, the same on every frame."""
    blotches = rng.integers(-45, 45, (H // 9 + 1, W // 9 + 1, 1)).astype(np.float32)
    return np.kron(blotches, np.ones((9, 9, 1), np.float32))[:H, :W] + np.array([80, 95, 105], np.float32)


def recording(cam: dict | None, *, frames: int = 5, face_r: float = 32, wobble: float = 3, seed: int = 1,
              full_face: bool = False) -> list[np.ndarray]:
    """Frames of a stream: the game everywhere, the webcam box `cam` (fractions) with a still room and the streamer's face
    moving a little; `full_face`: no game, a large face moving around (a camera filling the picture)."""
    rng = np.random.default_rng(seed)
    still = room(rng)
    out = []
    for i in range(frames):
        if full_face:
            img = still.copy()
            draw_face(img, W * (0.4 + 0.05 * i), H * 0.45, H * 0.13)
        else:
            img = game(rng, i).astype(np.float32)
            for box in ([] if cam is None else cam if isinstance(cam, list) else [cam]):
                x0, y0 = round(box["x"] * W), round(box["y"] * H)
                x1, y1 = round((box["x"] + box["width"]) * W), round((box["y"] + box["height"]) * H)
                img[y0:y1, x0:x1] = still[y0:y1, x0:x1]
                draw_face(img, (x0 + x1) / 2 + rng.uniform(-wobble, wobble), y0 + (y1 - y0) * 0.45 + rng.uniform(-wobble, wobble), face_r)
        img += rng.normal(0, 2, img.shape)
        out.append(np.clip(img, 0, 255).astype(np.uint8))
    return out


def close(a: dict, b: dict, tol: float = 0.02) -> bool:
    return all(abs(a[k] - b[k]) <= tol for k in ("x", "y", "width", "height"))


# --- the detector itself ---------------------------------------------------------------------------------------

def test_the_model_is_bundled_with_its_license_and_finds_a_drawn_face_but_not_a_blank_frame():
    assert faces.MODEL.is_file() and faces.MODEL.stat().st_size < 300_000
    assert "MIT License" in (faces.MODEL.parent / "LICENSE-YuNet.txt").read_text(encoding="utf-8")
    assert faces.detect(np.zeros((H, W, 3), np.uint8)) == []
    img = np.full((H, W, 3), (90, 110, 120), np.float32)
    draw_face(img, 300, 250, 45)
    img += np.random.default_rng(1).normal(0, 4, img.shape)
    [face] = faces.detect(np.clip(img, 0, 255).astype(np.uint8))
    assert face.score >= faces.SCORE and abs(face.centre[0] - 300 / W) < 0.02 and abs(face.centre[1] - 250 / H) < 0.04


def test_decode_reads_the_strides_and_keeps_one_box_per_face():
    """The YuNet outputs, as onnxruntime gives them, for a 64×64 input: one strong anchor at stride 8 (row 2, column 3)
    and its weaker twin next to it, which non-maximum suppression drops."""
    outs = {}
    for s in faces.STRIDES:
        n = (64 // s) ** 2
        outs[f"cls_{s}"], outs[f"obj_{s}"] = np.zeros((1, n, 1), np.float32), np.zeros((1, n, 1), np.float32)
        outs[f"bbox_{s}"], outs[f"kps_{s}"] = np.zeros((1, n, 4), np.float32), np.zeros((1, n, 10), np.float32)
    i = 2 * 8 + 3
    outs["cls_8"][0, i, 0] = outs["obj_8"][0, i, 0] = 0.9
    outs["bbox_8"][0, i] = (0.5, 0.5, np.log(2), np.log(3))            # centre (3.5, 2.5)·8, size 16 × 24
    outs["cls_8"][0, i + 1, 0] = outs["obj_8"][0, i + 1, 0] = 0.8
    outs["bbox_8"][0, i + 1] = (-0.4, 0.5, np.log(2), np.log(3))       # nearly the same box
    [(x, y, w, h, score)] = faces.decode(outs, 64)
    assert (x, y, w, h) == pytest.approx((28 - 8, 20 - 12, 16, 24), abs=1e-4) and score == pytest.approx(0.9)


def test_without_the_model_file_faces_say_so_and_do_not_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(faces, "MODEL", tmp_path / "missing.onnx")
    monkeypatch.setattr(faces, "_session", None)
    with pytest.raises(faces.FacesUnavailable, match="missing"):
        faces.detect(np.zeros((H, W, 3), np.uint8))


# --- the webcam box ------------------------------------------------------------------------------------------------

CAM_TOP_LEFT = {"x": 0.0, "y": 0.0, "width": 0.25, "height": 0.25 * 16 / 9 * 9 / 16 * 1.0}
CAM_LEFT_MIDDLE = {"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}
CAM_BOTTOM_RIGHT = {"x": 0.70, "y": 0.62, "width": 0.25, "height": 0.33}


@pytest.mark.parametrize("cam", [CAM_TOP_LEFT, CAM_LEFT_MIDDLE, CAM_BOTTOM_RIGHT], ids=["top-left", "left-middle", "bottom-right"])
def test_a_webcam_box_is_found_where_it_is(cam):
    found = look.look(recording(cam))
    assert found.kind == "overlay", found.reason
    assert close(found.camera, cam, 0.03) and look.inside(found.face, found.camera)
    # never wider than the real box by more than the search allows: no strip of the game in the webcam slot
    assert found.camera["x"] >= cam["x"] - 0.005 and found.camera["x"] + found.camera["width"] <= cam["x"] + cam["width"] + 0.005


def test_a_camera_filling_the_picture_is_no_webcam_box():
    found = look.look(recording(None, full_face=True))
    assert found.kind == "full" and found.camera is None and found.face["height"] >= look.BIG_FACE


def test_no_face_is_a_doubt_for_the_model():
    found = look.look(recording(None))
    assert found.kind == "unsure" and "no face" in found.reason


def test_two_webcam_boxes_are_a_doubt():
    found = look.look(recording([CAM_BOTTOM_RIGHT, {**CAM_BOTTOM_RIGHT, "y": 0.05}], seed=3))
    assert found.kind == "unsure" and found.candidates == 2 and "which one" in found.reason


def test_a_box_that_does_not_look_like_a_webcam_is_a_doubt_not_a_guess():
    strip = {"x": 0.0, "y": 0.0, "width": 0.17, "height": 1.0}          # a column from top to bottom: no webcam shape
    found = look.look(recording(strip))
    assert found.kind == "unsure" and found.candidates == 1 and "opposite sides" in found.reason


def test_a_webcam_found_before_is_used_again_without_looking_for_its_edges():
    cam = {"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}
    again = look.look(recording(CAM_LEFT_MIDDLE, seed=7), known=[cam])
    assert again.kind == "overlay" and again.known and again.camera == cam


def test_a_known_webcam_without_a_face_is_kept_when_its_box_is_still_there(monkeypatch):
    frames = recording(CAM_LEFT_MIDDLE, seed=8)
    monkeypatch.setattr(faces, "detect", lambda img, score=faces.SCORE: [])          # the streamer looks away
    found = look.look(frames, known=[CAM_LEFT_MIDDLE])
    assert found.kind == "overlay" and found.known and "still there" in found.reason
    plain = recording(None, seed=9)                                    # the webcam is gone: no box, a doubt
    assert look.look(plain, known=[CAM_LEFT_MIDDLE]).kind == "unsure"
    # an avatar the model found on frames with no face: frames with no face again are that webcam
    assert look.look(plain, known=[CAM_LEFT_MIDDLE], faceless=[CAM_LEFT_MIDDLE]).kind == "overlay"


def test_doubt_names_what_is_wrong_with_a_box():
    face = {"x": 0.05, "y": 0.4, "width": 0.04, "height": 0.09}
    assert look.doubt({"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.3}, face) == "no edge of a webcam on two opposite sides"
    assert "shape" in look.doubt({"x": 0.0, "y": 0.04, "width": 0.17, "height": 0.95}, face)
    assert "covers" in look.doubt({"x": 0.0, "y": 0.0, "width": 0.7, "height": 0.7}, face)
    assert look.doubt({"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}, face) is None


# --- the layout from it ---------------------------------------------------------------------------------------------

def test_the_layout_from_a_webcam_is_the_split_that_fits_it_with_the_camera_on_top():
    square = {"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}          # 326 × 313 px: the equal halves fit it best
    wide = {"x": 0.0, "y": 0.0, "width": 0.25, "height": 0.25}             # 480 × 270 px: the 640 px slot
    for cam, mode in ((square, "streamer_scene_split_equal"), (wide, "streamer_scene_split")):
        layout = from_frames(cam, {"x": cam["x"] + 0.05, "y": cam["y"] + 0.05, "width": 0.04, "height": 0.09})
        assert layout.mode == mode == best_split(cam) and mode in SLOTS
        s = layout.streamer_crop
        assert s["x"] >= cam["x"] - 1e-6 and s["x"] + s["width"] <= cam["x"] + cam["width"] + 1e-6     # only the camera on top
        sc = layout.scene_crop
        assert sc["x"] >= cam["x"] + cam["width"] - 1e-6 or sc["y"] >= cam["y"] + cam["height"] - 1e-6  # the scene beside it


def test_one_picture_is_cut_around_the_face_or_the_middle():
    face = {"x": 0.6, "y": 0.3, "width": 0.1, "height": 0.22}
    layout = from_frames(None, face)
    assert layout.mode == "scene_only" and layout.streamer_crop is None
    centre = layout.scene_crop["x"] + layout.scene_crop["width"] / 2
    assert abs(centre - 0.65) < 0.01 and layout.scene_crop["height"] == 1.0
    assert abs(from_frames(None, None).scene_crop["x"] + from_frames(None, None).scene_crop["width"] / 2 - 0.5) < 0.01


def test_bgr_reads_a_frame_at_the_work_size(tmp_path):
    import subprocess
    path = tmp_path / "f.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=640x360", "-frames:v", "1", str(path)],
                   check=True)
    img = look.bgr(path)
    assert img.shape == (H, W, 3) and img[10, 10, 2] > 200 and img[10, 10, 0] < 60
    with pytest.raises(RuntimeError, match="could not read"):
        look.bgr(tmp_path / "missing.jpg")
    assert camera.WORK_W == W
