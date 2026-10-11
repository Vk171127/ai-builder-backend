"""Patterns endpoints."""

from __future__ import annotations

from pathlib import Path

import yaml

from fastapi import APIRouter

router = APIRouter(tags=["Patterns"])


@router.get("/patterns")
async def get_patterns() -> dict[str, object]:
    """Return scam types and top behaviours from static rules config."""
    payload = yaml.safe_load(Path("ml/rules/rules.yaml").read_text(encoding="utf-8")) or {}
    rows = payload.get("rules", [])
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        scam_type = str(row.get("scam_type", "unknown"))
        grouped.setdefault(scam_type, {})
        for bucket in ("all_of", "any_of", "ordering"):
            for behaviour in row.get(bucket, []) or []:
                name = str(behaviour)
                grouped[scam_type][name] = grouped[scam_type].get(name, 0) + 1

    patterns: list[dict[str, object]] = []
    for scam_type, counts in grouped.items():
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        patterns.append({"scam_type": scam_type, "top_behaviours": [name for name, _ in ordered[:5]]})

    patterns.sort(key=lambda item: str(item["scam_type"]))
    return {"patterns": patterns}
