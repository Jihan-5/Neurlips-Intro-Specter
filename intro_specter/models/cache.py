"""SQLite-backed prompt-response cache, keyed by hash(prompt+model+temperature+seed).

A cache hit returns the original `CompletionResult` (with `cache_hit=True`) so the
caller can still log tokens accurately for the *original* call while paying nothing
for the lookup.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .base import CompletionResult


_SCHEMA = """
CREATE TABLE IF NOT EXISTS completions (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL DEFAULT (julianday('now'))
)
"""


def make_key(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    seed: int | None,
    max_tokens: int,
) -> str:
    blob = json.dumps(
        {
            "provider": provider,
            "model": model,
            "system": system,
            "user": user,
            "temperature": round(temperature, 6),
            "seed": seed,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()


class SQLiteCache:
    def __init__(self, path: str | Path = "cache/completions.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
        finally:
            conn.close()

    def get(self, key: str) -> CompletionResult | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM completions WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        data: dict[str, Any] = json.loads(row[0])
        result = CompletionResult(**data)
        result.cache_hit = True
        return result

    def put(self, key: str, result: CompletionResult) -> None:
        # Store a copy with cache_hit=False so future loads can flip it on read.
        payload = dataclasses.asdict(result)
        payload["cache_hit"] = False
        blob = json.dumps(payload, default=str)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO completions (key, payload) VALUES (?, ?)",
                (key, blob),
            )

    def __len__(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM completions").fetchone()[0]
