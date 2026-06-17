# NexusWF Automation

Desktop app for automating NexusWF and ILSL legal records workflows.

## Requirements

- Windows
- Python 3.10 or newer ([python.org](https://www.python.org/downloads/))

## Setup

Double-click `install.bat` (or run it from a terminal). It will:

1. Create a virtual environment in `.venv`
2. Install Python packages from `requirements.txt`
3. Download the Chromium browser for Playwright

## Run

Double-click `run.bat` to open the control panel.

## Control panel

The app opens a window with four tabs. Use **Save settings** before starting a run.

### Credentials

Login details for the automation.

- **NexusWF username / password** — required. Used to sign in to NexusWF and clock in/out.
- **Use same credentials for ILSL portal** — when checked, the ILSL fields are disabled and NexusWF credentials are reused for the legal records portal.
- **ILSL username / password** — only needed when the ILSL portal uses a different account.

### URLs

Where the browser should go.

- **NexusWF base URL** — main NexusWF app (default: `https://app.nexuswf.com`).
- **ILSL portal URL** — legal records list page on the ILSL portal.
- **ILSL entry URL (optional)** — direct link to the data-entry page. Leave blank to use the portal URL with `/entry` appended.

### Run

How long and how many tasks each automation run should perform.

- **Entry duration (hours)** — minimum time spent on each task (default 5 hours). The bot paces record entry to fill this window.
- **Continuous mode** — when enabled, runs multiple tasks back-to-back in one session.
- **Number of tasks** — how many tasks to run when continuous mode is on (1–20). Disabled when continuous mode is off (single task per run).
- **Keep browser open after finish (seconds)** — how long to leave the browser window open when a run ends, so you can review the result.

### Browser

Playwright browser options.

- **Headless browser** — run without a visible window. Leave unchecked for normal use while setting up or debugging.
- **Browser channel (optional)** — use an installed browser instead of bundled Chromium, e.g. `chrome` or `msedge`. Leave blank for the default Chromium.

### Start / Stop, Progress, and Log

Below the tabs:

- **Start** — saves settings and begins the workflow (login → clock in → download records → enter data → request new tasks).
- **Stop** — requests a graceful stop: clocks out and closes the browser.
- **Progress** — shows how many records are done and elapsed time vs. the task target.
- **Log** — live output from the current run.

## First use

1. Fill in **Credentials** and **URLs**.
2. Adjust **Run** and **Browser** options if needed.
3. Click **Save settings**, then **Start**.

Settings are saved in `.session/user_settings.json`.
