"""Console progress bars and execution reporting."""

from __future__ import annotations

import sys
import time
from typing import Dict, List


class ConsoleReporter:
    """Manages ASCII progress reporting and summary tables."""

    def __init__(self, is_tty: bool = True):
        self.is_tty = is_tty and sys.stdout.isatty()
        self._spinner = ("|", "/", "-", "\\")
        self._spin_idx = 0

    def stage(self, num: int, title: str) -> None:
        print(f"\n  ===== [TAHAP {num}] {title} =====")

    def info(self, msg: str) -> None:
        print(f"  > {msg}")

    def warn(self, msg: str) -> None:
        print(f"  (!) {msg}")

    def progress(self, current: int, total: int, label: str) -> None:
        if not self.is_tty:
            return
        total = max(1, total)
        percent = int(100 * current / total)
        bar_len = 28
        filled = int(bar_len * current / total)
        bar = "=" * filled + (">" if filled < bar_len else "") + " " * (bar_len - filled - (1 if filled < bar_len else 0))
        spin = self._spinner[self._spin_idx % len(self._spinner)]
        self._spin_idx += 1
        line = f"\r  [{bar}] {percent:3d}% ({current}/{total}) {spin} {label[:35]}"
        sys.stdout.write(line.ljust(79))
        sys.stdout.flush()

    def finish_progress(self) -> None:
        if self.is_tty:
            sys.stdout.write("\r" + " " * 79 + "\r")
            sys.stdout.flush()

    def print_summary(self, stages: List[Dict[str, str]], duration_sec: float) -> None:
        print("\n" + "=" * 65)
        print("  REKAPITULASI PROSES MICROSTOCK")
        print("=" * 65)
        fmt = "  {:<4} {:<24} {:<10} {}"
        print(fmt.format("No", "Tahap", "Status", "Keterangan"))
        print("  " + "-" * 63)
        for s in stages:
            print(fmt.format(str(s.get("no", "")), s.get("tahap", ""), s.get("status", ""), s.get("detail", "")))
        print("=" * 65)
        mins = int(duration_sec // 60)
        secs = int(duration_sec % 60)
        print(f"  Total Waktu: {mins}m {secs}s\n")
