"""Entry point — opens the desktop control panel."""

from __future__ import annotations

import sys

from ui.app import run_app


def main() -> int:
    try:
        run_app()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
