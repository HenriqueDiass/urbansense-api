from typing import Optional, List
from pydantic import BaseModel


class Detection(BaseModel):
    label: str
    confidence: float
    box: List[float]  # [x1, y1, x2, y2]


class PredictionResponse(BaseModel):
    status: str = "success"
    has_trash: bool
    has_pothole: bool
    detections: List[Detection] = []
    detection_result: Optional[str] = None
    audio_feedback: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None


class ReportData(BaseModel):
    report_id: str
    created_at: str
    status: str
    thumbnail_url: Optional[str] = None
    audio_feedback: Optional[str] = None
    detection_result: Optional[str] = None
    detections: List[Detection] = []


class ReportResponse(BaseModel):
    status: str
    message: Optional[str] = None
    code: Optional[str] = None
    audio_feedback: Optional[str] = None
    detection_result: Optional[str] = None
    has_trash: Optional[bool] = None
    has_pothole: Optional[bool] = None
    detections: List[Detection] = []
    data: Optional[ReportData] = None
