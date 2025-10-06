from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from ..oci_client_adapter import OCIClients

def list_focus_days(clients: OCIClients, tenancy_ocid: str, days_back: int) -> List[Dict]:
    ns = "bling"
    bucket = tenancy_ocid
    now = datetime.now(timezone.utc)
    out = []
    for i in range(days_back):
        d = (now - timedelta(days=i)).date()
        prefix = f"FOCUS/{d.year:04d}/{d.month:02d}/{d.day:02d}/"
        try:
            objs = clients.object_storage.list_objects(ns, bucket, prefix=prefix)
            size = sum(o.size for o in objs.data.objects)
            present = len(objs.data.objects) > 0
        except Exception:
            present = False
            size = 0
        out.append({"date": d.isoformat(), "present": present, "sizeBytes": size})
    out.reverse()
    return out
