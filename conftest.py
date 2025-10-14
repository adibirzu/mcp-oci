# Global pytest configuration for this repo
# - Ignore vendored OCI SDK sources and virtualenvs during test discovery

collect_ignore_glob = [
    "oci-python-sdk/**",
    ".venv/**",
    "build/**",
    "dist/**",
]

