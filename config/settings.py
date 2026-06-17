"""Application configuration loaded from the UI settings file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_ENTRY_DURATION_HOURS = 5.0
SETTINGS_PATH = _PROJECT_ROOT / ".session" / "user_settings.json"

_DEFAULTS: dict[str, Any] = {
    "username": "",
    "password": "",
    "base_url": "https://app.nexuswf.com",
    "ilsl_portal_url": "https://portal.ilsl.co.uk/legal/files/records/index",
    "ilsl_entry_url": "",
    "ilsl_username": "",
    "ilsl_password": "",
    "use_same_ilsl_credentials": True,
    "headless": False,
    "browser_channel": "",
    "entry_duration_hours": MIN_ENTRY_DURATION_HOURS,
    "continuous_mode": False,
    "task_count": 2,
    "keep_open_seconds": 5,
}


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
    ilsl_entry_url: str
    continuous_mode: bool
    task_count: int
    keep_open_seconds: int

    @property
    def entry_duration_seconds(self) -> float:
        return self.entry_duration_hours * 3600

    @classmethod
    def defaults(cls) -> dict[str, Any]:
        return dict(_DEFAULTS)

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        settings_path = path or SETTINGS_PATH
        data = cls._read_file(settings_path)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        merged = {**_DEFAULTS, **data}

        username = str(merged["username"]).strip()
        password = str(merged["password"]).strip()
        if not username or not password:
            raise ValueError("NexusWF username and password are required.")

        base_url = str(merged["base_url"]).strip().rstrip("/")
        ilsl_portal_url = str(merged["ilsl_portal_url"]).strip().rstrip("/")

        use_same = bool(merged.get("use_same_ilsl_credentials", True))
        ilsl_username = str(merged["ilsl_username"]).strip() or username
        ilsl_password = str(merged["ilsl_password"]).strip() or password
        if use_same:
            ilsl_username = username
            ilsl_password = password

        entry_duration_hours = float(merged["entry_duration_hours"])
        if entry_duration_hours < MIN_ENTRY_DURATION_HOURS:
            raise ValueError(
                f"Entry duration must be at least {MIN_ENTRY_DURATION_HOURS} hours."
            )

        ilsl_entry_url = str(merged.get("ilsl_entry_url", "")).strip().rstrip("/")
        if not ilsl_entry_url:
            portal_base = ilsl_portal_url.rsplit("/", 1)[0]
            ilsl_entry_url = f"{portal_base}/entry"

        channel = str(merged.get("browser_channel", "")).strip() or None
        task_count = max(1, int(merged.get("task_count", 2)))
        keep_open_seconds = max(0, int(merged.get("keep_open_seconds", 5)))

        downloads_dir = _PROJECT_ROOT / "downloads"
        downloads_dir.mkdir(exist_ok=True)

        session_dir = _PROJECT_ROOT / ".session"
        session_dir.mkdir(exist_ok=True)

        return cls(
            username=username,
            password=password,
            base_url=base_url,
            ilsl_portal_url=ilsl_portal_url,
            ilsl_username=ilsl_username,
            ilsl_password=ilsl_password,
            headless=bool(merged.get("headless", False)),
            browser_channel=channel,
            downloads_dir=downloads_dir,
            session_dir=session_dir,
            storage_state_path=session_dir / "storage.json",
            entry_progress_path=session_dir / "entry_progress.json",
            default_timeout_ms=30_000,
            entry_duration_hours=entry_duration_hours,
            ilsl_entry_url=ilsl_entry_url,
            continuous_mode=bool(merged.get("continuous_mode", False)),
            task_count=task_count,
            keep_open_seconds=keep_open_seconds,
        )

    @classmethod
    def save(cls, data: dict[str, Any], path: Path | None = None) -> None:
        settings_path = path or SETTINGS_PATH
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        merged = {**_DEFAULTS, **data}
        if merged.get("use_same_ilsl_credentials", True):
            merged["ilsl_username"] = ""
            merged["ilsl_password"] = ""

        temp = settings_path.with_suffix(".tmp")
        temp.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        temp.replace(settings_path)

    @classmethod
    def _read_file(cls, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return dict(_DEFAULTS)
        return json.loads(path.read_text(encoding="utf-8"))

    def to_form_dict(self) -> dict[str, Any]:
        """Serialize settings for the UI (password masked when unchanged)."""
        stored = self._read_file(SETTINGS_PATH)
        return {
            "username": self.username,
            "password": stored.get("password", ""),
            "base_url": self.base_url,
            "ilsl_portal_url": self.ilsl_portal_url,
            "ilsl_entry_url": stored.get("ilsl_entry_url", ""),
            "ilsl_username": stored.get("ilsl_username", ""),
            "ilsl_password": stored.get("ilsl_password", ""),
            "use_same_ilsl_credentials": stored.get("use_same_ilsl_credentials", True),
            "headless": self.headless,
            "browser_channel": self.browser_channel or "",
            "entry_duration_hours": self.entry_duration_hours,
            "continuous_mode": self.continuous_mode,
            "task_count": self.task_count,
            "keep_open_seconds": self.keep_open_seconds,
        }

    def with_updates(self, data: dict[str, Any]) -> Settings:
        stored = self._read_file(SETTINGS_PATH)
        merged = {**stored, **data}
        if not str(merged.get("password", "")).strip() and stored.get("password"):
            merged["password"] = stored["password"]
        if not str(merged.get("ilsl_password", "")).strip() and stored.get("ilsl_password"):
            merged["ilsl_password"] = stored["ilsl_password"]
        return self.from_dict(merged)
