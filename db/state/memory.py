"""In-memory state store for single-instance deployments."""

from __future__ import annotations

import time


class InMemoryStateStore:
    """Process-local state store; single-instance only (state is lost on restart)."""

    def __init__(self) -> None:
        self._kv: dict[str, tuple[object, float | None]] = {}
        self._z: dict[str, dict[str, int]] = {}
        self._s: dict[str, set[str]] = {}

    def get(self, key):
        item = self._kv.get(key)
        if item is None:
            return None
        value, exp = item
        if exp is not None and time.time() * 1000 > exp:
            self._kv.pop(key, None)
            return None
        return value

    def set(self, key, value, ex=None, px=None, nx=False):
        if nx and self.get(key) is not None:
            return False
        exp = None
        if ex is not None:
            exp = time.time() * 1000 + ex * 1000
        if px is not None:
            exp = time.time() * 1000 + px
        self._kv[key] = (value, exp)
        return True

    def zadd(self, key, mapping):
        self._z.setdefault(key, {}).update({m: int(s) for m, s in mapping.items()})

    def zrangebyscore(self, key, lo, hi):
        rows = sorted(((m, s) for m, s in self._z.get(key, {}).items() if lo <= s <= hi), key=lambda r: r[1])
        return [m for m, _ in rows]

    def zremrangebyscore(self, key, lo, hi):
        z = self._z.get(key, {})
        gone = [m for m, s in z.items() if lo <= s <= hi]
        for m in gone:
            z.pop(m)
        return len(gone)

    def sadd(self, key, *members):
        cur = self._s.setdefault(key, set())
        before = len(cur)
        cur.update(members)
        return len(cur) - before

    def sismember(self, key, member):
        return member in self._s.get(key, set())

    def delete(self, *keys):
        n = 0
        for key in keys:
            for store in (self._kv, self._z, self._s):
                if store.pop(key, None) is not None:
                    n += 1
        return n

    def keys(self, pattern):
        prefix = pattern.rstrip("*")
        found = {k for store in (self._kv, self._z, self._s) for k in store if k.startswith(prefix)}
        return sorted(found)

    def ping(self):
        return True
