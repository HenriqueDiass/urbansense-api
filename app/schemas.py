from typing import Optional

from pydantic import BaseModel


class Detection(BaseModel):
    label: str
    confidence: float
    box: list[float]  # [x1, y1, x2, y2]


class PredictionResponse(BaseModel):
    has_trash: bool
    has_pothole: bool
    detections: list[Detection]


class ReportData(BaseModel):
    report_id: str
    created_at: str
    status: str
    thumbnail_url: Optional[str] = None
    audio_feedback: Optional[str] = None
    detection_result: Optional[str] = None


class ReportResponse(BaseModel):
    """Shape the Android client already parses (see `NativeHttpDispatcher.parseSubmissionResponse`)
    — matching it means no client-side parsing changes were needed to add this endpoint."""

    status: str
    message: Optional[str] = None
    code: Optional[str] = None
    audio_feedback: Optional[str] = None
    detection_result: Optional[str] = None
    data: Optional[ReportData] = None
