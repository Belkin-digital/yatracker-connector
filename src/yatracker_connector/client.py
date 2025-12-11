"""Factory for TrackerClient instances."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from yandex_tracker_client import TrackerClient

from .config import Settings, get_settings


@lru_cache
def build_tracker_client(settings: Optional[Settings] = None) -> TrackerClient:
    """Instantiate TrackerClient with validated settings."""
    cfg = settings or get_settings()
    return TrackerClient(**cfg.to_tracker_kwargs())


__all__ = ["build_tracker_client"]
