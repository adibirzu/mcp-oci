import json
import oci
from datetime import datetime, timezone
from mcp_oci_common import get_oci_config

def usage_home_region_config(cfg: dict) -> dict:
    uc = dict(cfg)
    try:
        idc = oci.identity.IdentityClient(cfg)
        ten = cfg.get("tenancy")
        ten_data = idc.get_tenancy(ten).data
        hr_key = getattr(ten_data, "home_region_key", None)
        if hr_key:
            for r in idc.list_regions().data or []:
                if getattr(r, "key", None) == hr_key:
                    uc["region"] = getattr(r, "name", uc.get("region"))
                    break
        if "region" not in uc:
            subs = idc.list_region_subscriptions(ten)
            for s in getattr(subs, "data", []) or []:
                if getattr(s, "is_home_region", False):
                    uc["region"] = getattr(s, "region_name", None) or getattr(s, "region", uc.get("region"))
                    break
    except Exception:
        # Best effort; fall back to provided cfg region
        pass
    return uc

def main():
    try:
        cfg = get_oci_config()
        usage_cfg = usage_home_region_config(cfg)
        usage = oci.usage_api.UsageapiClient(usage_cfg)

        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # Usage API requires hours, minutes, seconds, and fractions to be 0 (00:00:00)
        # Set end to start of current day in UTC to satisfy precision
        end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=cfg.get("tenancy"),
            time_usage_started=start,
            time_usage_ended=end,
            granularity="DAILY",
            query_type="COST"
        )

        resp = usage.request_summarized_usages(request_summarized_usages_details=details)
        items = getattr(getattr(resp, "data", None), "items", []) or []

        total = 0.0
        currency = None
        daily = []
        for it in items:
            amt = float(getattr(it, "computed_amount", 0) or 0)
            total += amt
            if currency is None:
                cur = getattr(it, "currency", None)
                if cur:
                    currency = str(cur).strip()
            t = getattr(it, "time_usage_started", None)
            daily.append({
                "date": t.astimezone(timezone.utc).strftime("%Y-%m-%d") if t else "",
                "amount": amt
            })

        out = {
            "summary": f"Month-to-date cost: {total:.2f} {currency or 'USD'}",
            "total_cost_mtd": total,
            "currency": currency or "USD",
            "time_period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "granularity": "DAILY"
            },
            "daily_series": daily
        }
        print(json.dumps(out, indent=2))
    except oci.exceptions.ServiceError as e:
        print(json.dumps({"error": str(e), "type": "ServiceError"}, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e), "type": "Exception"}, indent=2))

if __name__ == "__main__":
    main()
