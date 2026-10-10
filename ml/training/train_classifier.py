"""Train calibrated LightGBM scam-type classifier and export ONNX."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import onnxmltools
import pyarrow.parquet as pq
from lightgbm import LGBMClassifier
from onnxmltools.convert.common.data_types import FloatTensorType
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, f1_score
from sklearn.preprocessing import LabelEncoder

from app.models.signal import Behaviour, SignalEvent
from app.schemas.feature import FEATURE_ORDER
from app.services.features.compute import compute


def _read_parquet(path: Path) -> list[dict[str, object]]:
    return pq.read_table(path).to_pylist()


def _to_signal_event(row: dict[str, object]) -> SignalEvent:
    attrs = json.loads(str(row["attrs"]))
    behaviour = Behaviour(str(row["behaviour"]))
    trust = int(row["trust"])
    return SignalEvent(
        timestamp_ms=int(row["ts_ms"]),
        signal_type=str(row["source"]),
        value_x100=trust,
        behaviour=behaviour,
        metadata=attrs,
    )


def _build_dataset(
    sessions: list[dict[str, object]],
    events: list[dict[str, object]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    events_by_session: dict[str, list[dict[str, object]]] = {}
    for event in events:
        session_id = str(event["session_id"])
        events_by_session.setdefault(session_id, []).append(event)

    vectors: list[list[int]] = []
    labels: list[str] = []
    start_ts: list[int] = []
    session_ids: list[str] = []

    for row in sessions:
        session_id = str(row["session_id"])
        session_events_rows = events_by_session.get(session_id, [])
        if not session_events_rows:
            continue

        session_events = [_to_signal_event(event_row) for event_row in session_events_rows]
        session_start = min(event.timestamp_ms for event in session_events)
        baseline_trust = int(sum((event.value_x100 or 0) for event in session_events) / len(session_events))
        fv = compute(
            events=session_events,
            context={"baseline_trust_x100": baseline_trust},
            config={},
        )
        vectors.append(fv.to_ordered_list())

        is_scam = bool(row["is_scam"])
        scam_type = str(row["scam_type"])
        labels.append(scam_type if is_scam else "benign")
        start_ts.append(session_start)
        session_ids.append(session_id)

    return (
        np.asarray(vectors, dtype=np.float32),
        np.asarray(labels, dtype=object),
        np.asarray(start_ts, dtype=np.int64),
        session_ids,
    )


def _time_split(start_ts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(start_ts)
    split_index = int(len(order) * 0.8)
    train_idx = order[:split_index]
    val_idx = order[split_index:]
    return train_idx, val_idx


def _split_calibration_eval(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pivot = max(1, len(indices) // 2)
    calib_idx = indices[:pivot]
    eval_idx = indices[pivot:]
    if len(eval_idx) == 0:
        eval_idx = calib_idx
    return calib_idx, eval_idx


def _inverse_frequency_weights(y_train: np.ndarray) -> dict[int, float]:
    classes, counts = np.unique(y_train, return_counts=True)
    total = float(np.sum(counts))
    num_classes = float(len(classes))
    weights: dict[int, float] = {}
    for cls, count in zip(classes, counts):
        weights[int(cls)] = total / (num_classes * float(count))
    return weights


def _export_model_card(
    out_path: Path,
    report: dict[str, dict[str, float] | float],
    macro_f1: float,
    train_count: int,
    val_count: int,
    class_names: list[str],
) -> None:
    lines = [
        "# Gatekeeper Classifier Model Card",
        "",
        "## Summary",
        "",
        "- Model: LightGBM multiclass + isotonic calibration (CalibratedClassifierCV)",
        f"- Classes ({len(class_names)}): {', '.join(class_names)}",
        f"- Train sessions: {train_count}",
        f"- Validation sessions: {val_count}",
        f"- Validation macro F1: {macro_f1:.4f}",
        "",
        "## Per-class metrics (validation)",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for class_name in class_names:
        metrics = report.get(class_name)
        if isinstance(metrics, dict):
            lines.append(
                f"| {class_name} | {metrics.get('precision', 0.0):.4f} | {metrics.get('recall', 0.0):.4f} | {metrics.get('f1-score', 0.0):.4f} | {int(metrics.get('support', 0.0))} |"
            )

    lines.extend(
        [
            "",
            "## Features",
            "",
            f"`{', '.join(FEATURE_ORDER)}`",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path("ml/simulator/out")
    sessions_path = root / "sessions.parquet"
    events_path = root / "events.parquet"
    if not sessions_path.exists() or not events_path.exists():
        raise FileNotFoundError("Expected simulator parquet files in ml/simulator/out/")

    sessions = _read_parquet(sessions_path)
    events = _read_parquet(events_path)
    x_all, y_text, ts, _ = _build_dataset(sessions=sessions, events=events)

    encoder = LabelEncoder()
    y_all = encoder.fit_transform(y_text)
    class_names = [str(c) for c in encoder.classes_]

    train_idx, val_idx = _time_split(ts)
    x_train, x_val_all = x_all[train_idx], x_all[val_idx]
    y_train, y_val_all = y_all[train_idx], y_all[val_idx]
    calib_idx, eval_idx = _split_calibration_eval(np.arange(len(x_val_all)))
    x_cal, y_cal = x_val_all[calib_idx], y_val_all[calib_idx]
    x_eval, y_eval = x_val_all[eval_idx], y_val_all[eval_idx]

    class_weights = _inverse_frequency_weights(y_train)
    sample_weight = np.asarray([class_weights[int(label)] for label in y_train], dtype=np.float64)

    base = LGBMClassifier(
        objective="multiclass",
        num_class=len(class_names),
        n_estimators=220,
        learning_rate=0.06,
        num_leaves=127,
        min_child_samples=10,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )
    base.fit(x_train, y_train, sample_weight=sample_weight)

    calibrated = CalibratedClassifierCV(base, method="isotonic", cv="prefit")
    calibrated.fit(x_cal, y_cal)

    y_pred = calibrated.predict(x_eval)
    report = classification_report(
        y_eval,
        y_pred,
        labels=np.arange(len(class_names)),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    macro_f1 = float(
        f1_score(
            y_eval,
            y_pred,
            labels=np.arange(len(class_names)),
            average="macro",
            zero_division=0,
        )
    )
    print("Validation metrics (per class):")
    for class_name in class_names:
        metrics = report.get(class_name)
        if isinstance(metrics, dict):
            print(
                f"- {class_name}: precision={metrics['precision']:.4f} recall={metrics['recall']:.4f} f1={metrics['f1-score']:.4f}"
            )
    print(f"Macro F1: {macro_f1:.4f}")

    model_dir = Path("ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = model_dir / "classifier.onnx"

    onnx_model = onnxmltools.convert_lightgbm(
        base.booster_,
        initial_types=[("features", FloatTensorType([None, x_train.shape[1]]))],
        target_opset=15,
    )
    onnx_path.write_bytes(onnx_model.SerializeToString())

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    preds = session.run(None, {input_name: x_eval[:8].astype(np.float32)})
    if not preds:
        raise RuntimeError("ONNX runtime produced no outputs")
    proba_output = preds[-1]
    if isinstance(proba_output, list):
        if not proba_output:
            raise RuntimeError("Expected non-empty ONNX probability output")
        if isinstance(proba_output[0], dict):
            matrix = np.asarray(
                [
                    [float(row.get(class_index, 0.0)) for class_index in range(len(class_names))]
                    for row in proba_output
                ],
                dtype=np.float32,
            )
        else:
            matrix = np.asarray(proba_output, dtype=np.float32)
    else:
        matrix = np.asarray(proba_output, dtype=np.float32)

    if matrix.ndim != 2:
        raise RuntimeError(f"Expected 2D probability array, got shape {matrix.shape}")
    print(f"ONNX sanity check passed. probability array shape: {matrix.shape}")

    _export_model_card(
        out_path=model_dir / "classifier_card.md",
        report=report,
        macro_f1=macro_f1,
        train_count=len(train_idx),
        val_count=len(eval_idx),
        class_names=class_names,
    )

    if macro_f1 <= 0.70:
        raise RuntimeError(f"Macro F1 {macro_f1:.4f} did not exceed 0.70")

    print(f"Saved ONNX model: {onnx_path}")
    print(f"Saved model card: {model_dir / 'classifier_card.md'}")


if __name__ == "__main__":
    main()
