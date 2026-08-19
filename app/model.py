"""Wrapper around the YOLO model used to detect trash and potholes."""
from __future__ import annotations

from pathlib import Path
from threading import Lock

from ultralytics import YOLO

MODEL_PATH = Path(__file__).resolve().parent.parent / "best.pt"

_model: YOLO | None = None
_lock = Lock()


def get_model() -> YOLO:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = YOLO(str(MODEL_PATH))
    return _model
