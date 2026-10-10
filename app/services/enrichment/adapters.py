"""External enrichment adapter interfaces and fake implementations."""

from typing import Protocol


class WebRisk(Protocol):
    async def lookup(self, value: str) -> dict[str, int | None]: ...


class MuleScore(Protocol):
    async def lookup(self, customer_id: str) -> dict[str, int | None]: ...


class RecentReports(Protocol):
    async def lookup(self, account_id: str) -> dict[str, int | None]: ...


class CustomerProfile(Protocol):
    async def lookup(self, customer_id: str) -> dict[str, int | None]: ...


class WebRiskFakeImpl:
    async def lookup(self, value: str) -> dict[str, int | None]:
        _ = value
        return {"risk_x100": 10}
