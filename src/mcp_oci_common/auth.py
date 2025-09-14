from typing import Optional, Type, Any

try:
    import oci  # type: ignore
except Exception:  # pragma: no cover
    oci = None


def get_config(profile: Optional[str] = None, region: Optional[str] = None) -> dict:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    cfg = oci.config.from_file(profile_name=profile)
    if region:
        cfg["region"] = region
    return cfg


def make_client(client_cls: Any, profile: Optional[str] = None, region: Optional[str] = None):
    cfg = get_config(profile=profile, region=region)
    return client_cls(cfg)
