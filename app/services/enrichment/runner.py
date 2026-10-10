"""Async enrichment execution runner."""

import asyncio


async def run_lookups(tasks: list[asyncio.Future]) -> list[object]:
    """Execute lookups with a global 80ms timeout budget."""
    if not tasks:
        return []
    done, _ = await asyncio.wait(tasks, timeout=0.08)
    return [task.result() for task in done if not task.cancelled()]
