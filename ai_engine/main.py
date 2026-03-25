import os
from datetime import datetime, timezone
from pathlib import Path

import cv2
import requests
import torch
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PREFERRED_MODEL_NAME = "yolov8m.pt"
FALLBACK_MODEL_NAME = "yolov8n.pt"

TRACKER_CONFIG = "bytetrack.yaml"
CONFIDENCE_THRESHOLD = 0.60
PERSON_CLASSES = [0]
LINE_RATIO_Y = 0.50
WINDOW_NAME = "OmniGuard AI - Sinir Kontrolu"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(PROJECT_ROOT / ".env")

BACKEND_API_URL = os.getenv("OMNIGUARD_BACKEND_URL", "http://localhost:8080/api/violations")
CAMERA_ID = os.getenv("OMNIGUARD_CAMERA_ID", "camera-01")
SITE_ID = os.getenv("OMNIGUARD_SITE_ID", "site-01")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OMNIGUARD_REQUEST_TIMEOUT", "3"))

DEVICE = 0 if torch.cuda.is_available() else "cpu"
DEVICE_NAME = "cuda:0" if torch.cuda.is_available() else "cpu"
HTTP = requests.Session()


def resolve_model_reference() -> str:
    preferred_local = BASE_DIR / PREFERRED_MODEL_NAME
    if preferred_local.exists():
        return str(preferred_local)

    preferred_project_level = PROJECT_ROOT / PREFERRED_MODEL_NAME
    if preferred_project_level.exists():
        return str(preferred_project_level)

    # If the medium model is not present locally, allow Ultralytics to resolve it.
    return PREFERRED_MODEL_NAME


def load_model() -> tuple[YOLO, str]:
    model_reference = resolve_model_reference()

    try:
        return YOLO(model_reference), Path(model_reference).name
    except Exception as exc:
        fallback_local = BASE_DIR / FALLBACK_MODEL_NAME
        if fallback_local.exists():
            print(
                f"Uyari: {PREFERRED_MODEL_NAME} yuklenemedi ({exc}). "
                f"{FALLBACK_MODEL_NAME} ile devam ediliyor."
            )
            return YOLO(str(fallback_local)), fallback_local.name
        fallback_project_level = PROJECT_ROOT / FALLBACK_MODEL_NAME
        if fallback_project_level.exists():
            print(
                f"Uyari: {PREFERRED_MODEL_NAME} yuklenemedi ({exc}). "
                f"{FALLBACK_MODEL_NAME} ile devam ediliyor."
            )
            return YOLO(str(fallback_project_level)), fallback_project_level.name
        raise


def has_crossed_line(previous_y: int | None, current_y: int, line_y: int) -> bool:
    return previous_y is not None and previous_y <= line_y < current_y


def build_violation_payload(
    track_id: int,
    confidence: float,
    frame_width: int,
    frame_height: int,
    line_y: int,
    center_x: int,
    center_y: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    model_name: str,
) -> dict:
    return {
        "eventType": "line_crossing",
        "cameraId": CAMERA_ID,
        "siteId": SITE_ID,
        "trackId": track_id,
        "confidence": round(confidence, 4),
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "device": DEVICE_NAME,
        "lineY": line_y,
        "frameWidth": frame_width,
        "frameHeight": frame_height,
        "center": {"x": center_x, "y": center_y},
        "boundingBox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
    }


def notify_backend(payload: dict) -> None:
    try:
        response = HTTP.post(
            BACKEND_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        print(
            f"Backend bildirimi gonderildi. status={response.status_code} "
            f"track_id={payload['trackId']}"
        )
    except requests.RequestException as exc:
        print(f"Backend bildirimi basarisiz. track_id={payload['trackId']} error={exc}")


model, loaded_model_name = load_model()
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Kamera acilamadi.")

previous_center_y_by_id: dict[int, int] = {}
violated_track_ids: set[int] = set()

print(
    f"OmniGuard AI basladi. model={loaded_model_name} device={DEVICE_NAME} "
    f"backend={BACKEND_API_URL}"
)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_height, frame_width = frame.shape[:2]
        line_y = int(frame_height * LINE_RATIO_Y)
        cv2.line(frame, (0, line_y), (frame_width, line_y), (255, 0, 0), 2)

        results = model.track(
            frame,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=CONFIDENCE_THRESHOLD,
            classes=PERSON_CLASSES,
            device=DEVICE,
            verbose=False,
        )

        active_track_ids: set[int] = set()

        for result in results:
            boxes = result.boxes
            if boxes is None or boxes.id is None:
                continue

            xyxy_list = boxes.xyxy.int().cpu().tolist()
            track_ids = boxes.id.int().cpu().tolist()
            confidences = boxes.conf.cpu().tolist()

            for (x1, y1, x2, y2), track_id, confidence in zip(xyxy_list, track_ids, confidences):
                active_track_ids.add(track_id)

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                previous_y = previous_center_y_by_id.get(track_id)
                crossed_line = has_crossed_line(previous_y, center_y, line_y)

                if crossed_line and track_id not in violated_track_ids:
                    violated_track_ids.add(track_id)

                    payload = build_violation_payload(
                        track_id=track_id,
                        confidence=confidence,
                        frame_width=frame_width,
                        frame_height=frame_height,
                        line_y=line_y,
                        center_x=center_x,
                        center_y=center_y,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        model_name=loaded_model_name,
                    )
                    print(
                        f"IHLAL! track_id={track_id} center_y={center_y} "
                        f"line_y={line_y} conf={confidence:.2f}"
                    )
                    notify_backend(payload)

                previous_center_y_by_id[track_id] = center_y

                is_violated = track_id in violated_track_ids
                color = (0, 0, 255) if is_violated else (0, 255, 0)
                status_text = "IHLAL" if is_violated else "IZLENIYOR"
                label = f"ID {track_id} {status_text} {confidence:.2f}"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )
                cv2.circle(frame, (center_x, center_y), 4, color, -1)

        stale_track_ids = [
            track_id
            for track_id in previous_center_y_by_id
            if track_id not in active_track_ids and track_id not in violated_track_ids
        ]
        for track_id in stale_track_ids:
            previous_center_y_by_id.pop(track_id, None)

        cv2.imshow(WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
