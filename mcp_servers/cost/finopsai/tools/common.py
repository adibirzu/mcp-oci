from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0
