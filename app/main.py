import io

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from PIL import Image

from app.model import get_model
from app.schemas import Detection, PredictionResponse

app = FastAPI(title="UrbanSense API", version="1.0.0")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    confidence: float = Query(0.25, ge=0.0, le=1.0, description="Minimum confidence threshold"),
) -> PredictionResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {file.content_type}")

    raw = await file.read()
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

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
