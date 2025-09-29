#!/usr/bin/env python3

import time
import os

try:
    import pyroscope
    pyroscope.configure(
        application_name="test-mcp-profiling",
        server_address="http://localhost:4040",
        sample_rate=100,  # 100 Hz
        detect_subprocesses=False,
        enable_logging=True,
    )
    print("✅ Pyroscope configured")

    # Create some CPU activity for profiling
    def cpu_intensive_task():
        result = 0
        for i in range(1000000):
            result += i ** 2
        return result

    print("🔄 Running CPU intensive task...")
    for _ in range(5):
        result = cpu_intensive_task()
        time.sleep(0.1)

    print("✅ Profile data should be available in Pyroscope")
    print("🌐 Check: http://localhost:4040")

except ImportError:
    print("❌ pyroscope-io package not installed")
    print("Install with: pip install pyroscope-io")
except Exception as e:
    print(f"❌ Error setting up profiling: {e}")