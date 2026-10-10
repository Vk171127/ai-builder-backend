"""Generate synthetic scam/benign sessions and event streams.

CLI:
    python -m ml.simulator.generate --scams 10000 --benign 100000 --seed 42
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


Behaviour = Literal["normal", "suspicious", "malicious"]
Source = Literal["phone", "extension", "server"]

SCAM_TYPES: tuple[str, ...] = (
    "digital_arrest_cbi",
    "digital_arrest_trai",
    "bank_official_vishing",
    "kyc_expiry_phishing",
    "investment_fake_app",
    "romance_scam",
    "bec_vendor",
    "remote_access_tech",
)

SCAM_STAGES: tuple[str, ...] = (
    "contact",
    "trust_building",
    "isolation",
    "pressure",
    "extraction",
)

BENIGN_SCENARIOS: tuple[str, ...] = (
    "rent_payment",
    "family_transfer",
    "utility_payment",
    "genuine_bank_call",
)


@dataclass(slots=True)
class StageGap:
    mean: float
    sigma: float


@dataclass(slots=True)
class StageConfig:
    behaviours: list[Behaviour]
    source: Source
    emission_prob: float
    gap_seconds: StageGap


@dataclass(slots=True)
class Scenario:
    scam_type: str
    stages: dict[str, StageConfig]


@dataclass(slots=True)
class UserProfile:
    user_id: str
    avg_payment_minor: int
    usual_hours: tuple[int, int]
    known_payees: list[str]
    tenure_days: int
    amount_history_minor: list[int]
    payee_history: set[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Gatekeeper simulator data")
    parser.add_argument("--scams", type=int, required=True, help="Number of scam sessions")
    parser.add_argument("--benign", type=int, required=True, help="Number of benign sessions")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic generation")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("ml/simulator/out"),
        help="Output directory for parquet files",
    )
    return parser.parse_args()


def _load_scenarios(root: Path) -> dict[str, Scenario]:
    scenarios: dict[str, Scenario] = {}
    for scam_type in SCAM_TYPES:
        path = root / f"{scam_type}.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        stage_map: dict[str, StageConfig] = {}
        for stage_name in SCAM_STAGES:
            stage_raw = raw["stages"][stage_name]
            behaviours = [str(value) for value in stage_raw["behaviours"]]
            stage_map[stage_name] = StageConfig(
                behaviours=behaviours,
                source=str(stage_raw["source"]),
                emission_prob=float(stage_raw["emission_prob"]),
                gap_seconds=StageGap(
                    mean=float(stage_raw["gap_seconds"]["mean"]),
                    sigma=float(stage_raw["gap_seconds"]["sigma"]),
                ),
            )
        scenarios[scam_type] = Scenario(scam_type=scam_type, stages=stage_map)
    return scenarios


def _build_profiles(rng: np.random.Generator, count: int = 1000) -> list[UserProfile]:
    profiles: list[UserProfile] = []
    for index in range(count):
        avg_payment_minor = int(max(5000, np.exp(rng.normal(9.0, 0.8))))
        start_hour = int(rng.integers(7, 20))
        end_hour = min(23, start_hour + int(rng.integers(2, 5)))
        known_count = int(rng.integers(4, 10))
        known_payees = [f"payee_{index}_{value}" for value in range(known_count)]
        history = [int(max(1000, rng.lognormal(np.log(avg_payment_minor), 0.25))) for _ in range(20)]
        profiles.append(
            UserProfile(
                user_id=f"user_{index:04d}",
                avg_payment_minor=avg_payment_minor,
                usual_hours=(start_hour, end_hour),
                known_payees=known_payees,
                tenure_days=int(rng.integers(30, 3650)),
                amount_history_minor=history,
                payee_history=set(known_payees),
            )
        )
    return profiles


def _sample_gap_ms(rng: np.random.Generator, gap: StageGap) -> int:
    seconds = float(rng.lognormal(mean=gap.mean, sigma=gap.sigma))
    return max(1, int(seconds * 1000))


def _choose_user(profiles: list[UserProfile], rng: np.random.Generator) -> UserProfile:
    return profiles[int(rng.integers(0, len(profiles)))]


def _compute_amount_outlier(user: UserProfile, amount_minor: int) -> bool:
    history = user.amount_history_minor
    if not history:
        return False
    baseline = float(np.median(np.array(history, dtype=np.float64)))
    return amount_minor > baseline * 2.5


def _compute_new_payee(user: UserProfile, payee_id: str) -> bool:
    return payee_id not in user.payee_history


def _draw_amount_for_stage(
    user: UserProfile,
    stage: str,
    is_scam: bool,
    rng: np.random.Generator,
) -> int:
    base = float(user.avg_payment_minor)
    if is_scam and stage == "extraction":
        return int(max(2000, rng.lognormal(np.log(base * 3.0), 0.55)))
    if is_scam and stage in {"pressure", "isolation"}:
        return int(max(2000, rng.lognormal(np.log(base * 1.8), 0.45)))
    return int(max(1000, rng.lognormal(np.log(base), 0.30)))


def _make_stage_event(
    *,
    session_id: str,
    user: UserProfile,
    stage: str,
    source: Source,
    behaviour: Behaviour,
    ts_ms: int,
    is_scam: bool,
    scam_type: str,
    payee_id: str,
    hard_negative: bool,
    rng: np.random.Generator,
) -> dict[str, object]:
    amount_minor = _draw_amount_for_stage(user=user, stage=stage, is_scam=is_scam, rng=rng)
    new_payee = _compute_new_payee(user, payee_id)
    amount_outlier = _compute_amount_outlier(user, amount_minor)

    trust = 65
    if behaviour == "suspicious":
        trust = 40
    elif behaviour == "malicious":
        trust = 15

    attrs: dict[str, object] = {
        "user_id": user.user_id,
        "stage": stage,
        "payee_id": payee_id,
        "amount_minor": amount_minor,
        "amount_x100": amount_minor * 100,
        "new_payee": new_payee,
        "amount_outlier": amount_outlier,
        "tenure_days": user.tenure_days,
        "hard_negative": hard_negative,
    }
    if is_scam:
        attrs["scam_type"] = scam_type

    user.amount_history_minor.append(amount_minor)
    if len(user.amount_history_minor) > 120:
        user.amount_history_minor.pop(0)
    user.payee_history.add(payee_id)

    return {
        "session_id": session_id,
        "ts_ms": ts_ms,
        "source": source,
        "behaviour": behaviour,
        "trust": trust,
        "attrs": json.dumps(attrs, sort_keys=True, separators=(",", ":")),
    }


def _simulate_scam_session(
    *,
    session_id: str,
    scenario: Scenario,
    user: UserProfile,
    start_ts_ms: int,
    rng: np.random.Generator,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    stage_points: list[dict[str, object]] = []
    ts_ms = start_ts_ms
    payee_id = f"scam_payee_{scenario.scam_type}_{int(rng.integers(0, 10_000_000))}"

    for stage in SCAM_STAGES:
        stage_cfg = scenario.stages[stage]
        emitted: list[Behaviour] = [
            behaviour
            for behaviour in stage_cfg.behaviours
            if float(rng.random()) <= stage_cfg.emission_prob
        ]
        if not emitted:
            emitted = [stage_cfg.behaviours[int(rng.integers(0, len(stage_cfg.behaviours)))]]

        for behaviour in emitted:
            ts_ms += _sample_gap_ms(rng, stage_cfg.gap_seconds)
            events.append(
                _make_stage_event(
                    session_id=session_id,
                    user=user,
                    stage=stage,
                    source=stage_cfg.source,
                    behaviour=behaviour,
                    ts_ms=ts_ms,
                    is_scam=True,
                    scam_type=scenario.scam_type,
                    payee_id=payee_id,
                    hard_negative=False,
                    rng=rng,
                )
            )
        stage_points.append({"ts_ms": ts_ms, "stage": stage})

    while len(events) < 5:
        stage = SCAM_STAGES[-1]
        stage_cfg = scenario.stages[stage]
        behaviour = stage_cfg.behaviours[int(rng.integers(0, len(stage_cfg.behaviours)))]
        ts_ms += _sample_gap_ms(rng, stage_cfg.gap_seconds)
        events.append(
            _make_stage_event(
                session_id=session_id,
                user=user,
                stage=stage,
                source=stage_cfg.source,
                behaviour=behaviour,
                ts_ms=ts_ms,
                is_scam=True,
                scam_type=scenario.scam_type,
                payee_id=payee_id,
                hard_negative=False,
                rng=rng,
            )
        )

    session_row = {
        "session_id": session_id,
        "scam_type": scenario.scam_type,
        "is_scam": True,
        "stage_at_each_ts": json.dumps(stage_points, separators=(",", ":")),
    }
    return session_row, events


def _simulate_benign_session(
    *,
    session_id: str,
    user: UserProfile,
    start_ts_ms: int,
    hard_negative: bool,
    rng: np.random.Generator,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    scenario_name = BENIGN_SCENARIOS[int(rng.integers(0, len(BENIGN_SCENARIOS)))]
    ts_ms = start_ts_ms
    events: list[dict[str, object]] = []
    stage_points: list[dict[str, object]] = []

    if hard_negative:
        stages = ["contact", "verification", "payment", "confirmation"]
        behaviours: list[Behaviour] = ["normal", "suspicious", "normal", "normal"]
        source_seq: list[Source] = ["extension", "phone", "server", "server"]
    else:
        stages = ["contact", "payment", "confirmation"]
        behaviours = ["normal", "normal", "normal"]
        source_seq = ["extension", "server", "server"]

    payee_from_history = sorted(user.payee_history)
    if hard_negative and float(rng.random()) < 0.65:
        payee_id = f"new_payee_{user.user_id}_{int(rng.integers(0, 1_000_000))}"
    else:
        payee_id = payee_from_history[int(rng.integers(0, len(payee_from_history)))]

    for index, stage in enumerate(stages):
        ts_ms += max(1, int(rng.lognormal(mean=1.0, sigma=0.35) * 1000))
        behaviour = behaviours[index]
        if hard_negative and index == 1 and float(rng.random()) < 0.5:
            behaviour = "malicious"

        events.append(
            _make_stage_event(
                session_id=session_id,
                user=user,
                stage=stage,
                source=source_seq[index],
                behaviour=behaviour,
                ts_ms=ts_ms,
                is_scam=False,
                scam_type="benign",
                payee_id=payee_id,
                hard_negative=hard_negative,
                rng=rng,
            )
        )
        stage_points.append({"ts_ms": ts_ms, "stage": stage})

    session_row = {
        "session_id": session_id,
        "scam_type": "hard_negative" if hard_negative else scenario_name,
        "is_scam": False,
        "stage_at_each_ts": json.dumps(stage_points, separators=(",", ":")),
    }
    return session_row, events


def _write_parquet_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd")


def generate(scams: int, benign: int, seed: int, out_dir: Path) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    scenarios = _load_scenarios(Path(__file__).resolve().parent / "scenarios")
    profiles = _build_profiles(rng, count=1000)

    sessions_rows: list[dict[str, object]] = []
    events_rows: list[dict[str, object]] = []
    base_ts_ms = 1_700_000_000_000
    total_sessions = scams + benign
    timeline_slots = rng.permutation(total_sessions)

    for index in range(scams):
        scam_type = SCAM_TYPES[index % len(SCAM_TYPES)]
        scenario = scenarios[scam_type]
        user = _choose_user(profiles, rng)
        session_id = f"scam_{index:07d}"
        start_ts = base_ts_ms + int(timeline_slots[index]) * 120_000
        session_row, session_events = _simulate_scam_session(
            session_id=session_id,
            scenario=scenario,
            user=user,
            start_ts_ms=start_ts,
            rng=rng,
        )
        sessions_rows.append(session_row)
        events_rows.extend(session_events)

    hard_negative_count = max(1, int(round(benign * 0.12)))
    for index in range(benign):
        user = _choose_user(profiles, rng)
        session_id = f"benign_{index:07d}"
        start_ts = base_ts_ms + int(timeline_slots[scams + index]) * 120_000
        hard_negative = index < hard_negative_count
        session_row, session_events = _simulate_benign_session(
            session_id=session_id,
            user=user,
            start_ts_ms=start_ts,
            hard_negative=hard_negative,
            rng=rng,
        )
        sessions_rows.append(session_row)
        events_rows.extend(session_events)

    sessions_path = out_dir / "sessions.parquet"
    events_path = out_dir / "events.parquet"

    _write_parquet_rows(sessions_path, sessions_rows)
    _write_parquet_rows(events_path, events_rows)

    return sessions_path, events_path


def main() -> None:
    args = _parse_args()
    sessions_path, events_path = generate(
        scams=args.scams,
        benign=args.benign,
        seed=args.seed,
        out_dir=args.out_dir,
    )
    print(f"wrote {sessions_path}")
    print(f"wrote {events_path}")


if __name__ == "__main__":
    main()
