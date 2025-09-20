#!/usr/bin/env python3
"""
Test connection to Autonomous JSON DB using wallet or DSN.

Wallet mode envs:
  ORACLE_DB_USER, ORACLE_DB_PASSWORD, ORACLE_DB_SERVICE,
  ORACLE_DB_WALLET_ZIP, ORACLE_DB_WALLET_PASSWORD

DSN mode envs:
  ORACLE_DB_USER, ORACLE_DB_PASSWORD, ORACLE_DB_DSN
"""
from __future__ import annotations

import os
import sys

def main() -> None:
    try:
        import oracledb
    except Exception as e:
        print(f"ERROR: python-oracledb not installed: {e}", file=sys.stderr)
        sys.exit(3)

    user = os.getenv("ORACLE_DB_USER")
    pwd = os.getenv("ORACLE_DB_PASSWORD")
    dsn = os.getenv("ORACLE_DB_DSN")
    svc = os.getenv("ORACLE_DB_SERVICE")
    wallet_zip = os.getenv("ORACLE_DB_WALLET_ZIP")
    wallet_pwd = os.getenv("ORACLE_DB_WALLET_PASSWORD")

    try:
        if wallet_zip and svc and user and pwd:
            import zipfile, tempfile
            tmp = tempfile.mkdtemp(prefix="mcp_wallet_")
            with zipfile.ZipFile(wallet_zip, 'r') as z:
                z.extractall(tmp)
            conn = oracledb.connect(user=user, password=pwd, dsn=svc, config_dir=tmp, wallet_location=tmp, wallet_password=wallet_pwd)
        else:
            conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
        cur = conn.cursor()
        cur.execute("select sys_context('userenv','service_name') svc, sysdate from dual")
        svc_name, now = cur.fetchone()
        print(f"OK: connected to {svc_name} at {now}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

