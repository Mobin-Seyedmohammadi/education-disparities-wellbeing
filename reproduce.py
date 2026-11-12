"""Rebuild the research outputs from frozen inputs, without network access."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for module in ["src.analysis", "src.measurement", "src.panel", "src.simulation", "src.verify", "src.make_report"]:
    print(f"Running {module}", flush=True)
    subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=True)
