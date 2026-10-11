"""Routing logic for deciding enrichment lookups."""

from app.models.signal import SignalEvent


def decide_lookups(events: list[SignalEvent]) -> list[str]:
    requested: set[str] = set()
    for event in events:
        metadata = event.metadata
        if metadata.get("payee_account"):
            requested.update(["mule_score", "recent_reports"])
        if metadata.get("referrer_url"):
            requested.add("web_risk")
        if metadata.get("domain"):
            requested.update(["web_risk", "domain_age"])
        if metadata.get("customer_id"):
            requested.add("customer_profile")
    return sorted(requested)
