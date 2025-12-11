"""Configuration helpers for TrackerClient."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

# Automatically load .env if present next to the project root.
_DOTENV_CANDIDATES = [
    Path(".env"),
    Path("config") / "local.env",
]

for candidate in _DOTENV_CANDIDATES:
    if candidate.exists():
        load_dotenv(candidate)


@dataclass(frozen=True)
class Settings:
    """Validated configuration for TrackerClient."""

    token: str
    org_id: Optional[str] = None
    cloud_org_id: Optional[str] = None
    api_url: str = "https://api.tracker.yandex.net/v3"

    def to_tracker_kwargs(self) -> Dict[str, str]:
        """Translate settings to TrackerClient kwargs."""
        if not self.cloud_org_id and not self.org_id:
            raise ValueError("Either org_id or cloud_org_id must be provided")

        kwargs: Dict[str, str] = {
            "token": self.token,
            "base_url": self.api_url,
        }

        if self.cloud_org_id:
            kwargs["cloud_org_id"] = self.cloud_org_id
        if self.org_id:
            kwargs["org_id"] = self.org_id
        return kwargs


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment variables."""
    token = os.getenv("YATRACKER_TOKEN")
    org_id = os.getenv("YATRACKER_ORG_ID")
    cloud_org_id = os.getenv("YATRACKER_CLOUD_ORG_ID")
    api_url = os.getenv("YATRACKER_API_URL", "https://api.tracker.yandex.net/v3")

    if not token:
        raise RuntimeError("YATRACKER_TOKEN is not set")

    return Settings(
        token=token.strip(),
        org_id=org_id.strip() if org_id else None,
        cloud_org_id=cloud_org_id.strip() if cloud_org_id else None,
        api_url=api_url.strip(),
    )


__all__ = ["Settings", "get_settings"]
