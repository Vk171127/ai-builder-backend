"""Intervention message construction with fallback chain."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.models.decision import Intervention
from db.state.store import StateStore


def _load_message(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return {str(k): str(v) for k, v in payload.items()}


def build_intervention(
    action: str,
    scam_type: str,
    language: str,
    state_store: StateStore | None,
) -> Intervention:
    if state_store is not None:
        cached = state_store.get(f"warn_cache:{scam_type}")
        if isinstance(cached, dict):
            title = str(cached.get("title", "Security warning"))
            body = str(cached.get("body", "Please review the transaction"))
            return Intervention(code=action, message=f"{title}: {body}")

    candidates = [
        Path("ml/messages") / scam_type / f"{language}.yml",
        Path("ml/messages") / scam_type / "en.yml",
        Path("ml/messages/unknown/en.yml"),
    ]
    for path in candidates:
        payload = _load_message(path)
        if payload is not None:
            return Intervention(
                code=action,
                message=f"{payload.get('title', 'Security warning')}: {payload.get('body', '')}",
            )

    return Intervention(code=action, message="Security warning: Please verify this payment.")
