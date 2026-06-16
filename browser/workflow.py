"""End-to-end automation: NexusWF login → clock in → legal records task download."""

from __future__ import annotations

import logging
from pathlib import Path

from browser.auth import ensure_logged_in
from browser.session import BrowserSession
from config.settings import Settings
from human.actor import HumanActor
from pages.dashboard import DashboardPage
from pages.legal_records import legal_records_page

logger = logging.getLogger(__name__)


async def run_workflow(session: BrowserSession, settings: Settings) -> Path | None:
    await ensure_logged_in(session, settings)

    dashboard = DashboardPage(session.page, session.human, settings.base_url)
    await dashboard.reload()

    work = await dashboard.open_records_work_tab(settings.ilsl_portal_url)

    records_human = HumanActor(work.records_tab)
    records = legal_records_page(work.records_tab, records_human, settings.ilsl_portal_url)
    await records.ensure_authenticated(settings.ilsl_username, settings.ilsl_password)
    downloaded = await records.download_task_if_needed(settings.downloads_dir)

    if work.clock_out_when_done:
        await dashboard.click_clock_out()

    return downloaded
