import io
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from app import config
from app.email_service import ReportEmailData, send_report_email, utc_now_iso
from app.model import get_model
from app.schemas import Detection, PredictionResponse, ReportData, ReportResponse

app = FastAPI(title="UrbanSense API", version="1.1.0")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

# Rótulos e feedback de voz por combinação de detecção — únicos, para /predict e /report não
# divergirem no texto que descreve a mesma imagem.
_DETECTION_LABELS = {
    (True, True): ("DESCARTE DE LIXO E BURACO NA VIA", "Atenção: Descarte irregular de lixo e buraco na pista detectados!"),
    (True, False): ("DESCARTE DE LIXO DETECTADO", "Descarte irregular de lixo identificado na via."),
    (False, True): ("BURACO NA VIA DETECTADO", "Atenção: Buraco na pista detectado."),
    (False, False): (None, "Vistoria concluída. Nenhum problema urbano detectado."),
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _run_detection(image: Image.Image, confidence: float) -> PredictionResponse:
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
    return PredictionResponse(
        has_trash=any("trash" in label for label in labels_found),
        has_pothole=any("pothole" in label for label in labels_found),
        detections=detections,
    )


def _load_image(raw: bytes, content_type: str | None) -> Image.Image:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    confidence: float = Query(0.25, ge=0.0, le=1.0, description="Minimum confidence threshold"),
) -> PredictionResponse:
    """Pure detection — no notification side effect. Kept as-is for any caller that only wants
    the YOLO result (e.g. batch analysis, another client)."""
    raw = await file.read()
    image = _load_image(raw, file.content_type)
    return _run_detection(image, confidence)


@app.post("/report")
async def report(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    timestamp: str | None = Form(None),
    trigger_type: str = Form("MANUAL"),
    device_id: str | None = Form(None),
    to_email: str | None = Form(None),
    confidence: float = Query(0.25, ge=0.0, le=1.0),
) -> JSONResponse:
    """Detection + citizen notification in one call — the route the Android app hits for every
    capture. Runs YOLO on the photo, then e-mails the city hall (Mailtrap) with the same photo
    attached and the GPS/detection metadata. The Mailtrap token stays server-side; the app never
    sees it.

    Detection failing is not fatal to the notification — an unrecognisable image still gets
    reported to the city hall with `detection_result: null`. E-mail failing IS reported as an
    error (502): that's the step the citizen actually cares about completing.
    """
    raw = await file.read()
    image = _load_image(raw, file.content_type)

    detection_result: str | None = None
    audio_feedback = "Vistoria concluída."
    try:
        prediction = _run_detection(image, confidence)
        detection_result, audio_feedback = _DETECTION_LABELS[(prediction.has_trash, prediction.has_pothole)]
    except Exception:
        # Detector unavailable/erroring must not block the citizen from notifying the city hall.
        pass

    report_id = "rep_" + uuid.uuid4().hex
    created_at = utc_now_iso()
    trigger_label = "Captura automática" if trigger_type.upper() == "AUTOMATIC" else "Captura manual"
    recipient = to_email or config.DEFAULT_CITY_HALL_EMAIL

    email_data = ReportEmailData(
        report_id=report_id,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        timestamp_iso=timestamp,
        trigger_label=trigger_label,
        device_id=device_id,
        city_hall_name=config.DEFAULT_CITY_HALL_NAME,
        detection_result=detection_result,
    )
    email_result = send_report_email(email_data, to_email=recipient, image_bytes=raw)

    if email_result.success:
        final_audio_feedback = (
            f"{audio_feedback} E-mail enviado para a {config.DEFAULT_CITY_HALL_NAME}."
            if detection_result
            else f"Registro enviado por e-mail para a {config.DEFAULT_CITY_HALL_NAME}."
        )
        body = ReportResponse(
            status="success",
            code="200",
            message="Ocorrência processada e notificada à prefeitura.",
            audio_feedback=final_audio_feedback,
            detection_result=detection_result,
            data=ReportData(
                report_id=report_id,
                created_at=created_at,
                status="QUEUED",
                audio_feedback=final_audio_feedback,
                detection_result=detection_result,
            ),
        )
        return JSONResponse(status_code=200, content=body.model_dump())

    body = ReportResponse(
        status="error",
        code="EMAIL_FAILED",
        message=f"Falha ao enviar e-mail via Mailtrap: {email_result.message}",
        audio_feedback="Falha ao enviar e-mail. Registro salvo localmente.",
        detection_result=detection_result,
    )
    return JSONResponse(status_code=502, content=body.model_dump())
