from typing import Any

try:
    import oci  # type: ignore
except Exception:  # pragma: no cover
    oci = None


def get_config(profile: str | None = None, region: str | None = None) -> dict:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    # Default to the standard SDK profile when none is provided
    profile_name = profile or "DEFAULT"
    cfg = oci.config.from_file(profile_name=profile_name)
    if region:
        cfg["region"] = region
    return cfg


def make_client(client_cls: Any, profile: str | None = None, region: str | None = None):
    cfg = get_config(profile=profile, region=region)
    return client_cls(cfg)
