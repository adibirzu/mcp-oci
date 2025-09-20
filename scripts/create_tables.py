#!/usr/bin/env python3
"""
Create tables in Autonomous DB using scripts/db_create_tables.sql.

Supports wallet or DSN connection (same envs as test_db_connection.py):
  ORACLE_DB_USER, ORACLE_DB_PASSWORD, ORACLE_DB_SERVICE,
  ORACLE_DB_WALLET_ZIP, ORACLE_DB_WALLET_PASSWORD
or
  ORACLE_DB_USER, ORACLE_DB_PASSWORD, ORACLE_DB_DSN
"""
from __future__ import annotations

import os
import sys

def main() -> None:
    import oracledb
    user = os.getenv("ORACLE_DB_USER"); pwd = os.getenv("ORACLE_DB_PASSWORD")
    dsn = os.getenv("ORACLE_DB_DSN"); svc = os.getenv("ORACLE_DB_SERVICE")
    wallet = os.getenv("ORACLE_DB_WALLET_ZIP"); wpwd = os.getenv("ORACLE_DB_WALLET_PASSWORD")

    if not (user and pwd and (svc or dsn)):
        print("ERROR: set ORACLE_DB_USER/ORACLE_DB_PASSWORD and ORACLE_DB_SERVICE (wallet) or ORACLE_DB_DSN", file=sys.stderr)
        sys.exit(2)

    conn = None
    if wallet and svc:
        import zipfile, tempfile
        tmp = tempfile.mkdtemp(prefix="mcp_wallet_")
        with zipfile.ZipFile(wallet, 'r') as z:
            z.extractall(tmp)
        conn = oracledb.connect(user=user, password=pwd, dsn=svc, config_dir=tmp, wallet_location=tmp, wallet_password=wpwd)
    else:
        conn = oracledb.connect(user=user, password=pwd, dsn=dsn)

    sql_path = os.path.join(os.path.dirname(__file__), 'db_create_tables.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()
    cur = conn.cursor()
    for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
        try:
            cur.execute(stmt)
        except Exception as e:
            # Ignore exists errors; print others
            if 'ORA-' in str(e):
                print(f"WARN: {e}")
    conn.commit()
    print("Tables created/verified")

if __name__ == '__main__':
    main()

