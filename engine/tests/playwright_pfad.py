"""Wo das Playwright-Modul für die Browsertests liegt: PLAYWRIGHT_MODUL, sonst ~/playwright-tool, sonst das global
installierte Paket (so in Cloud-Sitzungen). Ohne Fund werden die Browsertests übersprungen."""
import os
import shutil
import subprocess
from pathlib import Path


def finden():
    if os.environ.get("PLAYWRIGHT_MODUL"):
        return Path(os.environ["PLAYWRIGHT_MODUL"])
    eigen = Path.home() / "playwright-tool/node_modules/playwright/index.mjs"
    if eigen.exists() or not shutil.which("node"):
        return eigen
    try:
        js = subprocess.run(["node", "-p", "require.resolve('playwright')"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return eigen
    return Path(js).with_name("index.mjs") if js else eigen


PLAYWRIGHT = finden()
