from __future__ import annotations
from typing import List, Dict
from ..oci_client_adapter import OCIClients

def list_budgets_and_rules(clients: OCIClients, compartment_id: str) -> List[Dict]:
    budgets = clients.budgets.list_budgets(compartment_id=compartment_id).data
    out = []
    for b in budgets:
        rules = clients.budgets.list_alert_rules(b.id).data
        out.append({
            "name": b.display_name,
            "ocid": b.id,
            "amount": float(b.amount),
            "period": b.reset_period,
            "alerts": [{"threshold": float(r.threshold), "ruleType": r.type} for r in rules],
        })
    return out
