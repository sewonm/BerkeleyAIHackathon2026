"""
LangCache Service — semantic LLM response caching via Redis Iris LangCache.

Intercepts decision agent prompts and returns cached responses for semantically
similar market questions, skipping the LLM call entirely.

ENV VARS:
  LANGCACHE_SERVER_URL  (default: https://aws-us-east-1.langcache.redis.io)
  LANGCACHE_CACHE_ID
  LANGCACHE_API_KEY
"""

import os

_SERVER_URL = os.getenv("LANGCACHE_SERVER_URL", "https://aws-us-east-1.langcache.redis.io")
_CACHE_ID = os.getenv("LANGCACHE_CACHE_ID", "e0b51af4984543f49d70569c94404c33")
_API_KEY = os.getenv("LANGCACHE_API_KEY", "")


def cache_get(prompt: str):
    """Search LangCache for a semantically similar cached response. Returns string or None."""
    try:
        from langcache import LangCache
        with LangCache(server_url=_SERVER_URL, cache_id=_CACHE_ID, api_key=_API_KEY) as lc:
            result = lc.search(prompt=prompt)
            if result and result.data:
                return result.data[0].response
    except Exception:
        pass
    return None


def cache_set(prompt: str, response: str) -> bool:
    """Save a prompt-response pair to LangCache."""
    try:
        from langcache import LangCache
        with LangCache(server_url=_SERVER_URL, cache_id=_CACHE_ID, api_key=_API_KEY) as lc:
            lc.set(prompt=prompt, response=response)
            return True
    except Exception:
        return False
