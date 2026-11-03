"""Pure-ASCII console art: banner, progress bar, summary.

Art goes to the console only (never into JSON/CSV/log files) and is
silenced when stdout is not a TTY so piped output and pytest stay clean.
"""

from __future__ import annotations

import sys

BANNER = r"""
  ============================================================
   __  __ ___ ____ ____   ___  ____ _____ ___   ____ _  __
  |  \/  |_ _/ ___|  _ \ / _ \/ ___|_   _/ _ \ / ___| |/ /
  | |\/| || | |   | |_) | | | \___ \ | || | | | |   | ' /
  | |  | || | |___|  _ <| |_| |___) || || |_| | |___| . \
  |_|  |_|___\____|_| \_\\___/|____/ |_| \___/ \____|_|\_\
   MICROSTOCK-METADATA  -  local Qwen2.5-VL keywording
  ============================================================"""

BANNER_API = r"""
  ============================================================
   __  __ ___ ____ ____   ___  ____ _____ ___   ____ _  __
  |  \/  |_ _/ ___|  _ \ / _ \/ ___|_   _/ _ \ / ___| |/ /
  | |\/| || | |   | |_) | | | \___ \ | || | | | |   | ' /
  | |  | || | |___|  _ <| |_| |___) || || |_| | |___| . \
  |_|  |_|___\____|_| \_\\___/|____/ |_| \___/ \____|_|\_\
   MICROSTOCK-METADATA  -  API inference keywording
  ============================================================"""

DONE_ART = r"""
  ____   ___  _   _ _____
 |  _ \ / _ \| \ | | ____|
 | | | | | | |  \| |  _|
 | |_| | |_| | |\  | |___
 |____/ \___/|_| \_|_____|"""

_SPINNER = ("|", "/", "-", "\\")


def enabled() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def print_banner(model_id: str, device: str = "api", offline: bool = False, backend: str = "api") -> None:
    if not enabled():
        return
    print(BANNER_API)
    print(f"   model={model_id}  via API")
    print()


class ProgressBar:
    """Per-image progress bar with spinner. Pure ASCII, carriage-return."""

    def __init__(self, total: int, width: int = 24):
        self.total = total
        self.width = width
        self.tick = 0

    def show(self, done: int, label: str) -> None:
        if not enabled():
            return
        frac = done / self.total if self.total else 1.0
        fill = min(self.width, int(frac * self.width))
        if fill >= self.width:
            bar = "=" * self.width
        else:
            bar = "=" * fill + ">" + "-" * (self.width - fill - 1)
        spin = _SPINNER[self.tick % len(_SPINNER)]
        self.tick += 1
        if len(label) > 40:
            label = "..." + label[-37:]
        sys.stdout.write(f"\r[{bar}] {done}/{self.total} {spin} {label}   ")
        sys.stdout.flush()

    def finish(self) -> None:
        if enabled():
            sys.stdout.write("\n")
            sys.stdout.flush()


def print_summary(summary: dict) -> None:
    if not enabled():
        return
    print(DONE_ART)
    print(
        "   total={total} ok={successful} failed={failed} "
        "skipped={skipped} review={needs_review}".format(**summary)
    )
