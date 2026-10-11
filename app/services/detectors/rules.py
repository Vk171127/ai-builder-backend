"""Rules detector and linter."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.models.detection import Detection
from app.models.signal import Behaviour, SignalEvent


@dataclass(slots=True)
class Rule:
    id: str
    all_of: list[str]
    any_of: list[str]
    none_of: list[str]
    ordering: list[str]
    scam_type: str
    floor: float


def _load_rules(path: Path) -> list[Rule]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = payload.get("rules", [])
    output: list[Rule] = []
    for row in rows:
        output.append(
            Rule(
                id=str(row.get("id")),
                all_of=[str(value) for value in row.get("all_of", [])],
                any_of=[str(value) for value in row.get("any_of", [])],
                none_of=[str(value) for value in row.get("none_of", [])],
                ordering=[str(value) for value in row.get("ordering", [])],
                scam_type=str(row.get("scam_type", "unknown")),
                floor=float(row.get("floor", 0.0)),
            )
        )
    return output


def _behaviour_name(event: SignalEvent) -> str:
    return event.behaviour.value if event.behaviour is not None else ""


def _matches(rule: Rule, events: list[SignalEvent]) -> tuple[bool, list[str]]:
    names = [_behaviour_name(event) for event in events]
    ids_by_name: dict[str, list[str]] = {}
    for event in events:
        name = _behaviour_name(event)
        ids_by_name.setdefault(name, []).append(event.event_id)

    for needle in rule.all_of:
        if needle not in names:
            return False, []
    if rule.any_of and not any(needle in names for needle in rule.any_of):
        return False, []
    if any(needle in names for needle in rule.none_of):
        return False, []

    if rule.ordering:
        cursor = 0
        for expected in rule.ordering:
            try:
                idx = names.index(expected, cursor)
            except ValueError:
                return False, []
            cursor = idx + 1

    evidence: list[str] = []
    for needle in set(rule.all_of + rule.any_of + rule.ordering):
        evidence.extend(ids_by_name.get(needle, []))
    return True, sorted(set(evidence))


def detect_rules(events: list[SignalEvent], rules_path: Path = Path("ml/rules/rules.yaml")) -> Detection:
    rules = _load_rules(rules_path)
    best_floor = 0.0
    probs: dict[str, float] = {}
    evidence: list[str] = []

    for rule in rules:
        matched, ids = _matches(rule, events)
        if not matched:
            continue
        best_floor = max(best_floor, rule.floor)
        probs[rule.scam_type] = max(probs.get(rule.scam_type, 0.0), rule.floor)
        evidence.extend(ids)

    if not probs:
        probs = {"benign": 1.0}

    total = sum(probs.values())
    normalized = {key: value / total for key, value in probs.items()} if total > 0 else {"benign": 1.0}
    return Detection(
        detector="rules",
        score=best_floor,
        scam_type_probs=normalized,
        evidence_event_ids=sorted(set(evidence)),
    )


def lint_rules(rules_path: Path = Path("ml/rules/rules.yaml")) -> int:
    rules = _load_rules(rules_path)
    known = {member.value for member in Behaviour}
    unknown: set[str] = set()
    for rule in rules:
        for needle in rule.all_of + rule.any_of + rule.none_of + rule.ordering:
            if needle not in known:
                unknown.add(needle)
    if unknown:
        for name in sorted(unknown):
            print(f"Unknown Behaviour referenced in rules: {name}")
        return 1
    print("Rules lint passed")
    return 0


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["lint"])
    args = parser.parse_args()
    if args.command == "lint":
        return lint_rules()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
