import os
import time
from collections import deque
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


def get_env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def parse_source(source_value: str) -> int | str:
    return int(source_value) if source_value.isdigit() else source_value


def resolve_runtime_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate

    return BASE_DIR / candidate


load_env_file(PROJECT_ROOT / ".env")

TRACKER_CONFIG = os.getenv("OMNIGUARD_TRACKER_CONFIG", "bytetrack.yaml")
CONFIDENCE_THRESHOLD = float(os.getenv("OMNIGUARD_CONFIDENCE", "0.60"))
LINE_RATIO_Y = float(os.getenv("OMNIGUARD_LINE_RATIO_Y", "0.50"))
PERSON_CLASSES = [0]
SOURCE = parse_source(os.getenv("OMNIGUARD_SOURCE", "0"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OMNIGUARD_REQUEST_TIMEOUT", "3"))
BACKEND_API_URL = os.getenv("OMNIGUARD_BACKEND_URL", "http://localhost:8080/api/violations")
CAMERA_ID = os.getenv("OMNIGUARD_CAMERA_ID", "camera-01")
SITE_ID = os.getenv("OMNIGUARD_SITE_ID", "site-01")
SHOW_WINDOW = get_env_bool("OMNIGUARD_SHOW_WINDOW", True)
SAVE_SNAPSHOTS = get_env_bool("OMNIGUARD_SAVE_SNAPSHOTS", True)
SNAPSHOT_DIR = resolve_runtime_path(os.getenv("OMNIGUARD_SNAPSHOT_DIR", "artifacts/snapshots"))
VIOLATION_RETENTION_FRAMES = int(os.getenv("OMNIGUARD_VIOLATION_RETENTION_FRAMES", "300"))
FPS_SMOOTHING_WINDOW = int(os.getenv("OMNIGUARD_FPS_SMOOTHING_WINDOW", "20"))

DEVICE = 0 if torch.cuda.is_available() else "cpu"
DEVICE_NAME = "cuda:0" if torch.cuda.is_available() else "cpu"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "OmniGuardAI/0.1"})

if SAVE_SNAPSHOTS:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def resolve_model_reference(model_name: str) -> str:
    local_candidate = BASE_DIR / model_name
    if local_candidate.exists():
        return str(local_candidate)

    project_candidate = PROJECT_ROOT / model_name
    if project_candidate.exists():
        return str(project_candidate)

    return model_name


def load_model() -> tuple[YOLO, str]:
    preferred_reference = resolve_model_reference(PREFERRED_MODEL_NAME)

    try:
        return YOLO(preferred_reference), Path(preferred_reference).name
    except Exception as exc:
        fallback_reference = resolve_model_reference(FALLBACK_MODEL_NAME)
        if fallback_reference != FALLBACK_MODEL_NAME or Path(fallback_reference).exists():
            print(
                f"Uyari: {PREFERRED_MODEL_NAME} yuklenemedi ({exc}). "
                f"{Path(fallback_reference).name} ile devam ediliyor."
            )
            return YOLO(fallback_reference), Path(fallback_reference).name
        raise


def has_crossed_line(previous_y: int | None, current_y: int, line_y: int) -> bool:
    return previous_y is not None and previous_y <= line_y < current_y


def to_project_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def save_violation_snapshot(
    frame,
    line_y: int,
    track_id: int,
    confidence: float,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> tuple[str | None, str | None]:
    if not SAVE_SNAPSHOTS:
        return None, None

    timestamp_utc = datetime.now(timezone.utc)
    filename = f"{timestamp_utc.strftime('%Y%m%dT%H%M%S_%fZ')}_track_{track_id}.jpg"
    snapshot_path = SNAPSHOT_DIR / filename

    snapshot = frame.copy()
    cv2.line(snapshot, (0, line_y), (snapshot.shape[1], line_y), (255, 0, 0), 2)
    cv2.rectangle(snapshot, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(
        snapshot,
        f"IHLAL ID {track_id} {confidence:.2f}",
        (x1, max(24, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
    )

    if not cv2.imwrite(str(snapshot_path), snapshot):
        print(f"Snapshot kaydi basarisiz. track_id={track_id}")
        return None, None

    return to_project_relative_path(snapshot_path), timestamp_utc.isoformat()


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
    snapshot_path: str | None,
    snapshot_created_utc: str | None,
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
        "snapshotPath": snapshot_path,
        "snapshotCreatedUtc": snapshot_created_utc,
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


def draw_status_overlay(frame, model_name: str, smoothed_fps: float, alert_count: int) -> None:
    overlay_lines = [
        f"Model: {model_name}",
        f"Device: {DEVICE_NAME}",
        f"FPS: {smoothed_fps:.1f}",
        f"Alerts: {alert_count}",
    ]

    box_height = 30 + (len(overlay_lines) * 24)
    cv2.rectangle(frame, (10, 10), (245, box_height), (20, 20, 20), -1)

    for index, text in enumerate(overlay_lines):
        cv2.putText(
            frame,
            text,
            (20, 35 + (index * 22)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )


def cleanup_inactive_tracks(
    previous_center_y_by_id: dict[int, int],
    last_seen_frame_by_id: dict[int, int],
    violated_track_ids: set[int],
    current_frame_index: int,
) -> None:
    expired_track_ids = [
        track_id
        for track_id, last_seen_frame in last_seen_frame_by_id.items()
        if current_frame_index - last_seen_frame > VIOLATION_RETENTION_FRAMES
    ]

    for track_id in expired_track_ids:
        previous_center_y_by_id.pop(track_id, None)
        last_seen_frame_by_id.pop(track_id, None)
        violated_track_ids.discard(track_id)


def main() -> None:
    model, loaded_model_name = load_model()
    cap = cv2.VideoCapture(SOURCE)

    if not cap.isOpened():
        raise RuntimeError(f"Kamera veya kaynak acilamadi: {SOURCE}")

    previous_center_y_by_id: dict[int, int] = {}
    last_seen_frame_by_id: dict[int, int] = {}
    violated_track_ids: set[int] = set()
    fps_samples: deque[float] = deque(maxlen=max(1, FPS_SMOOTHING_WINDOW))
    current_frame_index = 0

    print(
        f"OmniGuard AI basladi. model={loaded_model_name} device={DEVICE_NAME} "
        f"backend={BACKEND_API_URL} source={SOURCE}"
    )

    try:
        while True:
            frame_started_at = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            current_frame_index += 1
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

            for result in results:
                boxes = result.boxes
                if boxes is None or boxes.id is None:
                    continue

                xyxy_list = boxes.xyxy.int().cpu().tolist()
                track_ids = boxes.id.int().cpu().tolist()
                confidences = boxes.conf.cpu().tolist()

                for (x1, y1, x2, y2), track_id, confidence in zip(xyxy_list, track_ids, confidences):
                    last_seen_frame_by_id[track_id] = current_frame_index

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    previous_y = previous_center_y_by_id.get(track_id)
                    crossed_line = has_crossed_line(previous_y, center_y, line_y)

                    if crossed_line and track_id not in violated_track_ids:
                        violated_track_ids.add(track_id)
                        snapshot_path, snapshot_created_utc = save_violation_snapshot(
                            frame=frame,
                            line_y=line_y,
                            track_id=track_id,
                            confidence=confidence,
                            x1=x1,
                            y1=y1,
                            x2=x2,
                            y2=y2,
                        )

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
                            snapshot_path=snapshot_path,
                            snapshot_created_utc=snapshot_created_utc,
                        )
                        print(
                            f"IHLAL! track_id={track_id} center_y={center_y} "
                            f"line_y={line_y} conf={confidence:.2f} snapshot={snapshot_path}"
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

            cleanup_inactive_tracks(
                previous_center_y_by_id=previous_center_y_by_id,
                last_seen_frame_by_id=last_seen_frame_by_id,
                violated_track_ids=violated_track_ids,
                current_frame_index=current_frame_index,
            )

            frame_latency_ms = (time.perf_counter() - frame_started_at) * 1000
            fps_samples.append(1000 / frame_latency_ms if frame_latency_ms else 0.0)
            smoothed_fps = sum(fps_samples) / len(fps_samples)
            draw_status_overlay(frame, loaded_model_name, smoothed_fps, len(violated_track_ids))

            if SHOW_WINDOW:
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
