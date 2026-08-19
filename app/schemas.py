from pydantic import BaseModel


class Detection(BaseModel):
    label: str
    confidence: float
    box: list[float]  # [x1, y1, x2, y2]


class PredictionResponse(BaseModel):
    has_trash: bool
    has_pothole: bool
    detections: list[Detection]
