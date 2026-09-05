"""Simulator package for SentinelGraph synthetic fraud and payment transaction generation."""

import sys
from pathlib import Path

# Controlled import-path adjustment:
# Ensure apps/api is accessible on sys.path so the simulator can resolve app.models
# without requiring manual PYTHONPATH modification from the repository root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_API_DIR = _REPO_ROOT / "apps" / "api"
if _API_DIR.is_dir() and str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))
