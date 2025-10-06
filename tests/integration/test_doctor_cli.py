import json
import os
import subprocess


def test_doctor_cli(oci_profile, oci_region):
    env = os.environ.copy()
    cmd = ["mcp-oci", "doctor", "--profile", oci_profile, "--region", oci_region]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data.get("status") == "ok"
    assert data.get("region") == oci_region

