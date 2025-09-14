from __future__ import annotations

import json
import re
from typing import Any


def parse_json_loose(text: str) -> Any | None:
    # 1) Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2) Line-by-line JSON
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            items.append(obj)
        except Exception:
            continue
    if items:
        return items
    # 3) Heuristic: first JSON-looking substring
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return None


def parse_kv_lines(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip()
    return data

