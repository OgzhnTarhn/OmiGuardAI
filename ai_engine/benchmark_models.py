import argparse
import json
import time
from pathlib import Path
from statistics import mean

import cv2
import torch
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_MODELS = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
DEFAULT_CLASSES = [0]
DEFAULT_CONFIDENCE = 0.60
DEFAULT_WARMUP_FRAMES = 10
DEFAULT_MEASURE_FRAMES = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark YOLOv8 variants for the OmniGuard AI line-crossing pipeline."
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Video source. Use camera index like 0 or a path to a video file.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model references to benchmark. Local paths or Ultralytics model names.",
    )
    parser.add_argument(
        "--mode",
        choices=["predict", "track"],
        default="track",
        help="Use track to reflect the live pipeline or predict for pure detection timing.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONFIDENCE,
        help="Confidence threshold.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        type=int,
        default=DEFAULT_CLASSES,
        help="Class filters. Default is person only.",
    )
    parser.add_argument(
        "--warmup-frames",
        type=int,
        default=DEFAULT_WARMUP_FRAMES,
        help="Frames ignored before measurement begins.",
    )
    parser.add_argument(
        "--measure-frames",
        type=int,
        default=DEFAULT_MEASURE_FRAMES,
        help="Number of frames used for measurement.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Inference image size.",
    )
    parser.add_argument(
        "--tracker",
        default="bytetrack.yaml",
        help="Tracker config used when mode=track.",
    )
    parser.add_argument(
        "--save-json",
        type=Path,
        help="Optional path for saving the benchmark report as JSON.",
    )
    return parser.parse_args()


def parse_source(source_value: str) -> int | str:
    return int(source_value) if source_value.isdigit() else source_value


def resolve_model_reference(model_name: str) -> str:
    candidate = Path(model_name)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    local_candidate = BASE_DIR / model_name
    if local_candidate.exists():
        return str(local_candidate)

    project_candidate = PROJECT_ROOT / model_name
    if project_candidate.exists():
        return str(project_candidate)

    return model_name


def open_capture(source: int | str) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"Video source acilamadi: {source}")
    return capture


def sync_device() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def run_inference(
    model: YOLO,
    frame,
    mode: str,
    confidence: float,
    classes: list[int],
    device: int | str,
    imgsz: int,
    tracker: str,
):
    if mode == "track":
        return model.track(
            frame,
            persist=True,
            tracker=tracker,
            conf=confidence,
            classes=classes,
            device=device,
            imgsz=imgsz,
            verbose=False,
        )

    return model.predict(
        frame,
        conf=confidence,
        classes=classes,
        device=device,
        imgsz=imgsz,
        verbose=False,
    )


def benchmark_model(
    model_reference: str,
    source: int | str,
    mode: str,
    confidence: float,
    classes: list[int],
    warmup_frames: int,
    measure_frames: int,
    imgsz: int,
    tracker: str,
    device: int | str,
) -> dict:
    resolved_model = resolve_model_reference(model_reference)
    model = YOLO(resolved_model)
    capture = open_capture(source)

    timings_ms: list[float] = []
    detections_per_frame: list[int] = []
    measured_frames = 0
    total_frames = warmup_frames + measure_frames
    frame_width = None
    frame_height = None

    try:
        while measured_frames < total_frames:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_width is None or frame_height is None:
                frame_height, frame_width = frame.shape[:2]

            sync_device()
            started_at = time.perf_counter()
            results = run_inference(
                model=model,
                frame=frame,
                mode=mode,
                confidence=confidence,
                classes=classes,
                device=device,
                imgsz=imgsz,
                tracker=tracker,
            )
            sync_device()
            elapsed_ms = (time.perf_counter() - started_at) * 1000

            if measured_frames >= warmup_frames:
                timings_ms.append(elapsed_ms)
                box_count = 0
                for result in results:
                    if result.boxes is not None and result.boxes.xyxy is not None:
                        box_count += len(result.boxes.xyxy)
                detections_per_frame.append(box_count)

            measured_frames += 1
    finally:
        capture.release()

    measured_count = len(timings_ms)
    if measured_count == 0:
        raise RuntimeError(
            f"Olcum yapilamadi. Model={model_reference} kaynak yeterli frame saglamadi."
        )

    avg_latency_ms = mean(timings_ms)
    fps = 1000 / avg_latency_ms if avg_latency_ms else 0.0

    return {
        "model": Path(resolved_model).name,
        "resolvedModel": resolved_model,
        "mode": mode,
        "device": "cuda:0" if device == 0 else str(device),
        "frameWidth": frame_width,
        "frameHeight": frame_height,
        "measuredFrames": measured_count,
        "avgLatencyMs": round(avg_latency_ms, 2),
        "minLatencyMs": round(min(timings_ms), 2),
        "maxLatencyMs": round(max(timings_ms), 2),
        "avgFps": round(fps, 2),
        "avgDetectionsPerFrame": round(mean(detections_per_frame), 2),
    }


def print_report(report: list[dict]) -> None:
    print()
    print("OmniGuard AI Benchmark")
    print("-" * 88)
    print(
        f"{'Model':<16}{'Mode':<10}{'Device':<10}{'FPS':>8}{'Avg ms':>10}"
        f"{'Min ms':>10}{'Max ms':>10}{'Avg det':>12}"
    )
    print("-" * 88)

    for item in report:
        print(
            f"{item['model']:<16}{item['mode']:<10}{item['device']:<10}"
            f"{item['avgFps']:>8.2f}{item['avgLatencyMs']:>10.2f}"
            f"{item['minLatencyMs']:>10.2f}{item['maxLatencyMs']:>10.2f}"
            f"{item['avgDetectionsPerFrame']:>12.2f}"
        )

    print("-" * 88)


def main() -> None:
    args = parse_args()
    source = parse_source(args.source)
    device = 0 if torch.cuda.is_available() else "cpu"

    report: list[dict] = []
    failures: list[dict] = []

    print(
        f"Benchmark basladi. source={args.source} mode={args.mode} "
        f"device={'cuda:0' if device == 0 else 'cpu'}"
    )

    for model_name in args.models:
        print(f"Model test ediliyor: {model_name}")
        try:
            result = benchmark_model(
                model_reference=model_name,
                source=source,
                mode=args.mode,
                confidence=args.conf,
                classes=args.classes,
                warmup_frames=args.warmup_frames,
                measure_frames=args.measure_frames,
                imgsz=args.imgsz,
                tracker=args.tracker,
                device=device,
            )
            report.append(result)
        except Exception as exc:
            failures.append({"model": model_name, "error": str(exc)})
            print(f"Basarisiz: {model_name} error={exc}")

    if report:
        report.sort(key=lambda item: item["avgLatencyMs"])
        print_report(report)

    if failures:
        print()
        print("Basarisiz Modeller")
        print("-" * 88)
        for failure in failures:
            print(f"{failure['model']}: {failure['error']}")

    if args.save_json:
        payload = {"report": report, "failures": failures}
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        args.save_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print()
        print(f"Rapor kaydedildi: {args.save_json}")


if __name__ == "__main__":
    main()
