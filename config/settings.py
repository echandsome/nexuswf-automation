"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_ENTRY_DURATION_HOURS = 5.0


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    base_url: str
    ilsl_portal_url: str
    ilsl_username: str
    ilsl_password: str
    headless: bool
    browser_channel: str | None
    downloads_dir: Path
    session_dir: Path
    storage_state_path: Path
    entry_progress_path: Path
    default_timeout_ms: int
    entry_duration_hours: float
    file_executor: str
    ilsl_entry_url: str

    @classmethod
    def load(cls, env_path: Path | None = None) -> Settings:
        load_dotenv(env_path or _PROJECT_ROOT / ".env")

        username = os.getenv("NEXUSWF_USERNAME", "").strip()
        password = os.getenv("NEXUSWF_PASSWORD", "").strip()
        base_url = os.getenv("NEXUSWF_BASE_URL", "https://app.nexuswf.com").rstrip("/")
        ilsl_portal_url = os.getenv(
            "ILSL_PORTAL_URL",
            "https://portal.ilsl.co.uk/legal/files/records/index",
        ).rstrip("/")
        ilsl_username = os.getenv("ILSL_USERNAME", "").strip() or username
        ilsl_password = os.getenv("ILSL_PASSWORD", "").strip() or password

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

        entry_duration_hours = float(
            os.getenv("ENTRY_DURATION_HOURS", str(MIN_ENTRY_DURATION_HOURS))
        )
        if entry_duration_hours < MIN_ENTRY_DURATION_HOURS:
            raise ValueError(
                f"ENTRY_DURATION_HOURS must be at least {MIN_ENTRY_DURATION_HOURS} "
                f"(got {entry_duration_hours})."
            )

        file_executor = os.getenv("FILE_EXECUTOR", "Krzysztof Bednarczuk").strip()
        ilsl_entry_url = os.getenv("ILSL_ENTRY_URL", "").strip().rstrip("/")
        if not ilsl_entry_url:
            portal_base = ilsl_portal_url.rsplit("/", 1)[0]
            ilsl_entry_url = f"{portal_base}/entry"

        return cls(
            username=username,
            password=password,
            base_url=base_url,
            ilsl_portal_url=ilsl_portal_url,
            ilsl_username=ilsl_username,
            ilsl_password=ilsl_password,
            headless=headless,
            browser_channel=channel,
            downloads_dir=downloads_dir,
            session_dir=session_dir,
            storage_state_path=session_dir / "storage.json",
            entry_progress_path=session_dir / "entry_progress.json",
            default_timeout_ms=30_000,
            entry_duration_hours=entry_duration_hours,
            file_executor=file_executor,
            ilsl_entry_url=ilsl_entry_url,
        )

    @property
    def entry_duration_seconds(self) -> float:
        return self.entry_duration_hours * 3600
