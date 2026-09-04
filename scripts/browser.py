"""Browser checks with a separate worker; API and console must already be running."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
worker = subprocess.Popen(
    [sys.executable, "-m", "apps.worker.main"],
    cwd=ROOT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    result = subprocess.run(["npm", "run", "e2e"], cwd=ROOT / "apps/web")
finally:
    worker.terminate()
    worker.wait(timeout=10)
raise SystemExit(result.returncode)
