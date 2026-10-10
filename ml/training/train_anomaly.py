"""Train benign-profile anomaly model (IsolationForest)."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pyarrow.parquet as pq
from sklearn.ensemble import IsolationForest

from app.models.signal import Behaviour, SignalEvent
from app.services.features.compute import compute


def _read_parquet(path: Path) -> list[dict[str, object]]:
    return pq.read_table(path).to_pylist()


def _to_signal_event(row: dict[str, object]) -> SignalEvent:
    attrs = json.loads(str(row["attrs"]))
    return SignalEvent(
        timestamp_ms=int(row["ts_ms"]),
        signal_type=str(row["source"]),
        value_x100=int(row["trust"]),
        behaviour=Behaviour(str(row["behaviour"])),
        metadata=attrs,
    )


def main() -> None:
    sim_dir = Path("ml/simulator/out")
    sessions_path = sim_dir / "sessions.parquet"
    events_path = sim_dir / "events.parquet"
    if not sessions_path.exists() or not events_path.exists():
        raise FileNotFoundError("Expected simulator parquet files in ml/simulator/out/")

    sessions = _read_parquet(sessions_path)
    events = _read_parquet(events_path)

    benign_session_ids = {
        str(row["session_id"]) for row in sessions if not bool(row["is_scam"])
    }
    events_by_session: dict[str, list[dict[str, object]]] = {}
    for row in events:
        session_id = str(row["session_id"])
        if session_id in benign_session_ids:
            events_by_session.setdefault(session_id, []).append(row)

    matrix: list[list[int]] = []
    for session_id in sorted(benign_session_ids):
        session_rows = events_by_session.get(session_id)
        if not session_rows:
            continue
        signal_events = [_to_signal_event(row) for row in session_rows]
        baseline_trust = int(sum((event.value_x100 or 0) for event in signal_events) / len(signal_events))
        fv = compute(signal_events, context={"baseline_trust_x100": baseline_trust}, config={})
        matrix.append(fv.to_ordered_list())

    x = np.asarray(matrix, dtype=np.float32)
    if x.size == 0:
        raise RuntimeError("No benign feature rows available for anomaly training")

    model = IsolationForest(
        n_estimators=300,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x)

    model_dir = Path("ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    out_path = model_dir / "anomaly_iforest.joblib"
    joblib.dump(model, out_path)

    loaded = joblib.load(out_path)
    sample_scores = loaded.score_samples(x[:8])
    print(f"Saved anomaly model: {out_path}")
    print(f"Loaded model sanity check passed. score_samples len={len(sample_scores)}")


if __name__ == "__main__":
    main()
