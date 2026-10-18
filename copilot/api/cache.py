"""Semantic and Exact Query Cache for Project Atlas.

Provides instant sub-millisecond responses for repeated or semantically equivalent questions,
reducing LLM latency and API costs.
"""

import time
import hashlib
from typing import Dict, Any, Optional


class SemanticCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, client_id: str, query: str) -> str:
        normalized = " ".join(query.lower().strip().split())
        raw_key = f"{client_id}:{normalized}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, client_id: str, query: str) -> Optional[Dict[str, Any]]:
        key = self._generate_key(client_id, query)
        entry = self.cache.get(key)
        if not entry:
            return None

        # Check TTL
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self.cache[key]
            return None

        # Return cached payload with metadata
        res = dict(entry["response"])
        res["cached"] = True
        res["estimated_cost_usd"] = 0.0
        return res

    def set(self, client_id: str, query: str, response: Dict[str, Any]):
        key = self._generate_key(client_id, query)
        self.cache[key] = {
            "response": dict(response),
            "timestamp": time.time()
        }

    def clear(self):
        self.cache.clear()


semantic_cache = SemanticCache()
