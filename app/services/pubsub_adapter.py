"""Pub/Sub adapter for decision and outcome events."""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache

from google.cloud import pubsub_v1

from app.core.config import settings


class PubSubAdapter:
    def __init__(self) -> None:
        self._publisher = pubsub_v1.PublisherClient()

    def _publish(self, topic: str, payload: dict[str, object]) -> None:
        path = topic if topic.startswith("projects/") else self._publisher.topic_path(settings.gcp_project, topic)
        self._publisher.publish(path, json.dumps(payload, default=str).encode("utf-8")).result(timeout=5)

    async def publish_decision(self, payload: dict[str, object]) -> None:
        await asyncio.to_thread(self._publish, settings.effective_pubsub_topic_decisions, payload)

    async def publish_outcome(self, payload: dict[str, object]) -> None:
        await asyncio.to_thread(self._publish, settings.effective_pubsub_topic_outcomes, payload)


@lru_cache(maxsize=1)
def get_pubsub_adapter() -> PubSubAdapter:
    return PubSubAdapter()
