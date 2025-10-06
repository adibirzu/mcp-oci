#!/usr/bin/env python3
print("[ARCHIVED] populate_db_from_mcp.py is deprecated and not part of MCP deployment.")
raise SystemExit(0)

def main() -> None:
    user = os.getenv("ORACLE_DB_USER")
    pwd = os.getenv("ORACLE_DB_PASSWORD")
    dsn = os.getenv("ORACLE_DB_DSN")
    svc = os.getenv("ORACLE_DB_SERVICE")
    wallet_zip = os.getenv("ORACLE_DB_WALLET_ZIP")
    wallet_pwd = os.getenv("ORACLE_DB_WALLET_PASSWORD")
    wallet_dir = None
    if wallet_zip and svc and user and pwd:
        # Use wallet-based TCPS Thin connection
        import zipfile
        import tempfile
        tmp = tempfile.mkdtemp(prefix="mcp_wallet_")
        with zipfile.ZipFile(wallet_zip, 'r') as z:
            z.extractall(tmp)
        wallet_dir = tmp
    elif not (user and pwd and dsn):
        print("ERROR: Provide either wallet-based envs (ORACLE_DB_WALLET_ZIP, ORACLE_DB_SERVICE, ORACLE_DB_USER, ORACLE_DB_PASSWORD) or direct DSN envs (ORACLE_DB_USER, ORACLE_DB_PASSWORD, ORACLE_DB_DSN)", file=sys.stderr)
        sys.exit(2)

    try:
        import oracledb
    except Exception as e:
        print(f"ERROR: python-oracledb not installed: {e}", file=sys.stderr)
        sys.exit(3)

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from mcp_servers.inventory.server import list_all_discovery, generate_compute_capacity_report
    from mcp_servers.cost.server import get_cost_summary

    comp = os.getenv("COMPARTMENT_OCID")
    disc = list_all_discovery(compartment_id=comp, limit_per_type=1000)

    if wallet_dir:
        conn = oracledb.connect(user=user, password=pwd, dsn=svc, config_dir=wallet_dir, wallet_location=wallet_dir, wallet_password=wallet_pwd)
    else:
        conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    cur = conn.cursor()

    def upsert(table, rows, cols):
        if not rows:
            return
        placeholders = ",".join([":"+str(i+1) for i in range(len(cols))])
        sql = f"MERGE INTO {table} t USING (SELECT {placeholders} FROM dual) s ON (t.id = s.column1) " \
              f"WHEN MATCHED THEN UPDATE SET " + ",".join([f"t.{c}=s.column{i+1}" for i,c in enumerate(cols, start=1)]) + \
              " WHEN NOT MATCHED THEN INSERT (" + ",".join(cols) + ") VALUES (" + ",".join([f"s.column{i+1}" for i in range(1,len(cols)+1)]) + ")"
        for r in rows:
            cur.execute(sql, r)

    # Prepare rows
    def map_items(items, mapping):
        out = []
        for it in items:
            row = []
            for k in mapping:
                row.append(it.get(k) or it.get("_"+k))
            out.append(tuple(row))
        return out

    vcns = disc.get("vcns", {}).get("items", [])
    subnets = disc.get("subnets", {}).get("items", [])
    sec = disc.get("security_lists", {}).get("items", [])
    inst = disc.get("instances", {}).get("items", [])
    lbs = disc.get("load_balancers", {}).get("items", [])
    fnapps = disc.get("functions_apps", {}).get("items", [])
    streams = disc.get("streams", {}).get("items", [])

    upsert("vcns", map_items(vcns, ["id","display_name","compartment_id","cidr_block"]), ["id","display_name","compartment_id","cidr_block"])
    upsert("subnets", map_items(subnets, ["id","display_name","compartment_id","vcn_id","cidr_block"]), ["id","display_name","compartment_id","vcn_id","cidr_block"])
    upsert("instances", map_items(inst, ["id","display_name","compartment_id","shape","lifecycle_state","availability_domain"]), ["id","display_name","compartment_id","shape","lifecycle_state","availability_domain"])
    upsert("load_balancers", map_items(lbs, ["id","display_name","compartment_id","shape"]), ["id","display_name","compartment_id","shape"])
    upsert("functions_apps", map_items(fnapps, ["id","display_name","compartment_id"]), ["id","display_name","compartment_id"])
    upsert("streams", map_items(streams, ["id","name","compartment_id"]), ["id","name","compartment_id"])

    costs = get_cost_summary()
    if isinstance(costs, str):
        costs = json.loads(costs)
    cur.execute("INSERT INTO costs_summary(as_of,total_cost,currency) VALUES (SYSTIMESTAMP,:1,:2)", [costs.get("total_cost",0), costs.get("currency","USD")])

    # Capacity summary
    cap = generate_compute_capacity_report(compartment_id=comp)
    if isinstance(cap, str):
        cap = json.loads(cap)
    try:
        summary = {
            'total': cap.get('total_instances', 0),
            'running': cap.get('instances_by_state', {}).get('RUNNING', 0),
            'stopped': cap.get('instances_by_state', {}).get('STOPPED', 0),
            'shapes_used': len(cap.get('instances_by_shape', {})),
        }
        cur.execute(
            "INSERT INTO capacity_report(as_of,compartment_id,total_instances,running_instances,stopped_instances,shapes_used) "
            "VALUES (SYSTIMESTAMP,:1,:2,:3,:4,:5)",
            [comp or '', summary['total'], summary['running'], summary['stopped'], summary['shapes_used']]
        )
    except Exception:
        pass

    conn.commit()
    print("Populate complete")

if __name__ == "__main__":
    main()
