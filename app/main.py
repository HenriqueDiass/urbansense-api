import io
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from app import config
from app.email_service import ReportEmailData, send_report_email, utc_now_iso
from app.model import get_model
from app.schemas import Detection, PredictionResponse, ReportData, ReportResponse

app = FastAPI(title="UrbanSense API", version="1.2.0")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

_DETECTION_LABELS = {
    (True, True): ("DESCARTE DE LIXO E BURACO NA VIA", "Atenção: Descarte irregular de lixo e buraco na pista detectados!"),
    (True, False): ("DESCARTE DE LIXO DETECTADO", "Descarte irregular de lixo identificado na via."),
    (False, True): ("BURACO NA VIA DETECTADO", "Atenção: Buraco na pista detectado."),
    (False, False): (None, "Vistoria concluída. Nenhum problema urbano detectado."),
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _run_detection(image: Image.Image, confidence: float):
    model = get_model()
    results = model.predict(image, conf=confidence, verbose=False)
    result = results[0]

    detections: list[Detection] = []
    for box in result.boxes:
        label = model.names[int(box.cls[0])]
        detections.append(
            Detection(
                label=label,
                confidence=float(box.conf[0]),
                box=[float(v) for v in box.xyxy[0].tolist()],
            )
        )

    labels_found = {d.label.lower() for d in detections}
    has_trash = any("trash" in label for label in labels_found)
    has_pothole = any("pothole" in label for label in labels_found)

    detection_result, audio_feedback = _DETECTION_LABELS.get((has_trash, has_pothole), (None, "Vistoria concluída."))
    return has_trash, has_pothole, detections, detection_result, audio_feedback


def _load_image(raw: bytes, content_type: str | None) -> Image.Image:
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")


@app.post("/predict")
@app.post("/report")
async def process_report(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    accuracy: Optional[float] = Form(None),
    timestamp: Optional[str] = Form(None),
    trigger_type: str = Form("MANUAL"),
    device_id: Optional[str] = Form(None),
    to_email: Optional[str] = Form(None),
    confidence: float = Query(0.25, ge=0.0, le=1.0),
) -> JSONResponse:
    raw = await file.read()
    image = _load_image(raw, file.content_type)

    has_trash, has_pothole, detections, detection_result, audio_feedback = _run_detection(image, confidence)

    report_id = "rep_" + uuid.uuid4().hex
    created_at = utc_now_iso()
    trigger_label = "Captura automática" if (trigger_type and trigger_type.upper() == "AUTOMATIC") else "Captura manual"
    recipient = to_email or config.DEFAULT_CITY_HALL_EMAIL

    # E-mail notification dispatch if Mailtrap (SMTP sandbox or Sending API) is configured
    if config.EMAIL_CONFIGURED and recipient:
        email_data = ReportEmailData(
            report_id=report_id,
            latitude=latitude or 0.0,
            longitude=longitude or 0.0,
            accuracy=accuracy,
            timestamp_iso=timestamp or created_at,
            trigger_label=trigger_label,
            device_id=device_id,
            city_hall_name=config.DEFAULT_CITY_HALL_NAME,
            detection_result=detection_result,
        )
        send_report_email(email_data, to_email=recipient, image_bytes=raw)

    response_body = {
        "status": "success",
        "code": "200",
        "message": "Ocorrência processada com sucesso.",
        "audio_feedback": audio_feedback,
        "detection_result": detection_result,
        "has_trash": has_trash,
        "has_pothole": has_pothole,
        "detections": [d.model_dump() for d in detections],
        "data": {
            "report_id": report_id,
            "created_at": created_at,
            "status": "QUEUED",
            "audio_feedback": audio_feedback,
            "detection_result": detection_result,
            "detections": [d.model_dump() for d in detections],
        },
    }
    return JSONResponse(status_code=200, content=response_body)
