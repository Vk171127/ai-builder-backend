"""Firestore-backed state store (session windows, belief state, locks, warning cache)."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Protocol

os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")


@dataclass(slots=True)
class TokenBucketResult:
    allowed: bool
    remaining: int


class StateStore(Protocol):
    """Operations the pipeline needs from a working-state store."""

    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object, ex: int | None = None, px: int | None = None, nx: bool = False) -> bool: ...
    def zadd(self, key: str, mapping: dict[str, int]) -> None: ...
    def zrangebyscore(self, key: str, min_score: int, max_score: int) -> list[str]: ...
    def zremrangebyscore(self, key: str, min_score: int, max_score: int) -> int: ...
    def sadd(self, key: str, *members: str) -> int: ...
    def sismember(self, key: str, member: str) -> bool: ...
    def delete(self, *keys: str) -> int: ...
    def keys(self, pattern: str) -> list[str]: ...
    def ping(self) -> bool: ...


class FirestoreStateStore:
    """Firestore store exposing the key/value, sorted-set and set operations the pipeline uses."""

    def __init__(self, *, project: str, database: str, collection_prefix: str) -> None:
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency/env specific
            raise RuntimeError("google-cloud-firestore is not installed") from exc
        global AlreadyExists
        from google.api_core.exceptions import AlreadyExists  # type: ignore

        self._client = firestore.Client(project=project or None, database=database or None)
        self._kv_col = f"{collection_prefix}_kv"
        self._z_col = f"{collection_prefix}_zsets"
        self._set_col = f"{collection_prefix}_sets"

    @staticmethod
    def _encode(value: object) -> str:
        if hasattr(value, "model_dump"):
            value = value.model_dump()  # type: ignore[assignment]
        return json.dumps(value)

    @staticmethod
    def _decode(value: str | None) -> object | None:
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    def _doc_get(self, col: str, key: str) -> dict[str, object] | None:
        snap = self._client.collection(col).document(key).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        expires_at_ms = data.get("expires_at_ms")
        if isinstance(expires_at_ms, int) and int(time.time() * 1000) > expires_at_ms:
            self._client.collection(col).document(key).delete()
            return None
        return data

    def get(self, key: str) -> object | None:
        doc = self._doc_get(self._kv_col, key)
        if doc is None:
            return None
        payload = doc.get("payload")
        if isinstance(payload, str):
            return self._decode(payload)
        return payload

    def set(
        self,
        key: str,
        value: object,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
    ) -> bool:
        expires_at_ms: int | None = None
        now_ms = int(time.time() * 1000)
        if ex is not None:
            expires_at_ms = now_ms + ex * 1000
        if px is not None:
            expires_at_ms = now_ms + px
        ref = self._client.collection(self._kv_col).document(key)
        data = {"payload": self._encode(value), "expires_at_ms": expires_at_ms}
        if nx:
            # create() fails atomically if the doc exists; reclaim it only if expired.
            try:
                ref.create(data)
                return True
            except AlreadyExists:
                if self._doc_get(self._kv_col, key) is not None:
                    return False
        ref.set(data)
        return True

    def zadd(self, key: str, mapping: dict[str, int]) -> None:
        doc = self._doc_get(self._z_col, key) or {}
        entries = doc.get("entries")
        rows: list[dict[str, object]] = []
        if isinstance(entries, list):
            rows = [dict(item) for item in entries if isinstance(item, dict)]
        by_member = {str(row.get("member")): row for row in rows}
        for member, score in mapping.items():
            by_member[str(member)] = {"member": str(member), "score": int(score)}
        self._client.collection(self._z_col).document(key).set({"entries": list(by_member.values())})

    def zrangebyscore(self, key: str, min_score: int, max_score: int) -> list[str]:
        doc = self._doc_get(self._z_col, key) or {}
        entries = doc.get("entries")
        if not isinstance(entries, list):
            return []
        rows = [
            (str(item.get("member")), int(item.get("score", 0)))
            for item in entries
            if isinstance(item, dict)
        ]
        rows = [row for row in rows if min_score <= row[1] <= max_score]
        rows.sort(key=lambda item: item[1])
        return [member for member, _ in rows]

    def zremrangebyscore(self, key: str, min_score: int, max_score: int) -> int:
        doc = self._doc_get(self._z_col, key) or {}
        entries = doc.get("entries")
        if not isinstance(entries, list):
            return 0
        kept: list[dict[str, object]] = []
        removed = 0
        for item in entries:
            if not isinstance(item, dict):
                continue
            score = int(item.get("score", 0))
            if min_score <= score <= max_score:
                removed += 1
            else:
                kept.append(item)
        self._client.collection(self._z_col).document(key).set({"entries": kept})
        return removed

    def sadd(self, key: str, *members: str) -> int:
        doc = self._doc_get(self._set_col, key) or {}
        raw = doc.get("members")
        current = set(str(item) for item in raw) if isinstance(raw, list) else set()
        before = len(current)
        for member in members:
            current.add(member)
        self._client.collection(self._set_col).document(key).set({"members": sorted(current)})
        return len(current) - before

    def sismember(self, key: str, member: str) -> bool:
        doc = self._doc_get(self._set_col, key) or {}
        raw = doc.get("members")
        current = set(str(item) for item in raw) if isinstance(raw, list) else set()
        return member in current

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            for col in (self._kv_col, self._z_col, self._set_col):
                ref = self._client.collection(col).document(key)
                if ref.get().exists:
                    ref.delete()
                    deleted += 1
        return deleted

    def keys(self, pattern: str) -> list[str]:
        if not pattern.endswith("*"):
            return [pattern] if self.get(pattern) is not None else []
        prefix = pattern[:-1]
        found: set[str] = set()
        for col in (self._kv_col, self._z_col, self._set_col):
            for snap in self._client.collection(col).stream():
                key = snap.id
                if key.startswith(prefix):
                    found.add(key)
        return sorted(found)

    def ping(self) -> bool:
        next(self._client.collections(), None)
        return True


class FirestoreAnalysisStore:
    """Writes one flat analysis record per decision to a dedicated collection."""

    def __init__(self, *, project: str, database: str) -> None:
        self._project = project
        self._database = database
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        # Built lazily on first write so the gRPC channel is created in the serving
        # process, not before any reload/fork.
        with self._lock:
            if self._client is None:
                from google.cloud import firestore  # type: ignore

                self._client = firestore.Client(project=self._project or None, database=self._database or None)
            return self._client

    def put_document(self, collection: str, doc_id: str, data: dict[str, object]) -> None:
        last_exc: Exception | None = None
        for _ in range(2):
            try:
                self._get_client().collection(collection).document(doc_id).set(data, timeout=10)
                return
            except Exception as exc:  # deadline/unavailable: rebuild the channel and retry once
                last_exc = exc
                with self._lock:
                    self._client = None
        raise last_exc  # type: ignore[misc]


def get_analysis_store(*, project: str, database: str) -> FirestoreAnalysisStore:
    return FirestoreAnalysisStore(project=project, database=database)


def get_state_store(*, backend: str, project: str, database: str, collection_prefix: str) -> StateStore:
    """Return the working-state store: in-memory (default) or Firestore-backed."""
    if backend.strip().lower() == "firestore":
        store = FirestoreStateStore(project=project, database=database, collection_prefix=collection_prefix)
        store.ping()
        return store
    from db.state.memory import InMemoryStateStore

    return InMemoryStateStore()


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def token_bucket(
    state_store: StateStore | None,
    key: str,
    now_ms: int,
    *,
    limit: int,
    window_ms: int,
) -> TokenBucketResult:
    """Token-bucket style limiter implemented with sorted-set timestamps."""
    if state_store is None:
        return TokenBucketResult(allowed=True, remaining=limit)

    try:
        min_score = now_ms - window_ms
        state_store.zremrangebyscore(key, -10**18, min_score)
        used = len(state_store.zrangebyscore(key, min_score, now_ms))
        if used >= limit:
            return TokenBucketResult(allowed=False, remaining=0)

        marker = f"{now_ms}:{used}:{hash_key(key)[:8]}"
        state_store.zadd(key, {marker: now_ms})
        return TokenBucketResult(allowed=True, remaining=max(0, limit - used - 1))
    except Exception:
        return TokenBucketResult(allowed=True, remaining=limit)
