"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    base_url: str
    headless: bool
    browser_channel: str | None
    downloads_dir: Path
    session_dir: Path
    storage_state_path: Path
    default_timeout_ms: int

    @classmethod
    def load(cls, env_path: Path | None = None) -> Settings:
        load_dotenv(env_path or _PROJECT_ROOT / ".env")

        username = os.getenv("NEXUSWF_USERNAME", "").strip()
        password = os.getenv("NEXUSWF_PASSWORD", "").strip()
        base_url = os.getenv("NEXUSWF_BASE_URL", "https://app.nexuswf.com").rstrip("/")

        if not username or not password:
            raise ValueError(
                "NEXUSWF_USERNAME and NEXUSWF_PASSWORD must be set in .env "
                "(copy .env.example to .env and fill in credentials)."
            )

        headless = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
        channel = os.getenv("BROWSER_CHANNEL", "").strip() or None

        downloads_dir = _PROJECT_ROOT / "downloads"
        downloads_dir.mkdir(exist_ok=True)

        session_dir = _PROJECT_ROOT / ".session"
        session_dir.mkdir(exist_ok=True)

        return cls(
            username=username,
            password=password,
            base_url=base_url,
            headless=headless,
            browser_channel=channel,
            downloads_dir=downloads_dir,
            session_dir=session_dir,
            storage_state_path=session_dir / "storage.json",
            default_timeout_ms=30_000,
        )
