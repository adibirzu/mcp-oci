"""In-memory name -> OCID registry shared across MCP servers.

Purpose: Reduce redundant SDK/REST calls and let users refer to resources by
human-friendly names. The registry is process-local and ephemeral; persistence
is handled by the generic MCPCache if needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, List, Tuple, Iterable


@dataclass
class NameRegistry:
    compartments_by_name: Dict[str, str] = field(default_factory=dict)
    compartments_by_id: Dict[str, str] = field(default_factory=dict)

    vcns_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)
    subnets_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)
    nsgs_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)

    instances_by_name: Dict[Tuple[str, str], List[str]] = field(default_factory=dict)

    # Optional extended mappings for other services (lightweight)
    users_by_name: Dict[str, str] = field(default_factory=dict)
    clusters_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)
    applications_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)
    streams_by_name: Dict[Tuple[str, str], str] = field(default_factory=dict)

    _lock: RLock = field(default_factory=RLock)

    # ------------- Compartment helpers -------------
    def update_compartments(self, items: Iterable[dict]) -> None:
        with self._lock:
            for c in items:
                cid = c.get("id") or c.get("_id") or c.get("ocid")
                name = c.get("name") or c.get("_name") or c.get("display_name") or c.get("_display_name")
                if not cid or not name:
                    continue
                self.compartments_by_name[name] = cid
                self.compartments_by_id[cid] = name

    def resolve_compartment(self, name: str) -> str | None:
        with self._lock:
            return self.compartments_by_name.get(name)

    # ------------- Networking helpers -------------
    def update_vcns(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for v in items:
                vid = v.get("id") or v.get("_id")
                name = v.get("display_name") or v.get("_display_name") or v.get("name") or v.get("_name")
                if not vid or not name:
                    continue
                self.vcns_by_name[(compartment_id, name)] = vid

    def resolve_vcn(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.vcns_by_name.get((compartment_id, name))

    def update_subnets(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for s in items:
                sid = s.get("id") or s.get("_id")
                name = s.get("display_name") or s.get("_display_name") or s.get("name") or s.get("_name")
                if not sid or not name:
                    continue
                self.subnets_by_name[(compartment_id, name)] = sid

    def resolve_subnet(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.subnets_by_name.get((compartment_id, name))

    def update_nsgs(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for n in items:
                nid = n.get("id") or n.get("_id")
                name = n.get("display_name") or n.get("_display_name") or n.get("name") or n.get("_name")
                if not nid or not name:
                    continue
                self.nsgs_by_name[(compartment_id, name)] = nid

    def resolve_nsg(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.nsgs_by_name.get((compartment_id, name))

    # ------------- Compute helpers -------------
    def update_instances(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for i in items:
                iid = i.get("id") or i.get("_id")
                name = (
                    i.get("display_name")
                    or i.get("_display_name")
                    or i.get("hostname")
                    or i.get("_hostname")
                    or i.get("name")
                    or i.get("_name")
                )
                if not iid or not name:
                    continue
                key = (compartment_id, name)
                self.instances_by_name.setdefault(key, []).append(iid)

    def resolve_instance(self, compartment_id: str, name: str) -> List[str]:
        with self._lock:
            return list(self.instances_by_name.get((compartment_id, name), []))

    # ------------- IAM users -------------
    def update_users(self, items: Iterable[dict]) -> None:
        with self._lock:
            for u in items:
                uid = u.get("id") or u.get("_id")
                name = u.get("name") or u.get("_name") or u.get("login") or u.get("_login")
                if uid and name:
                    self.users_by_name[name] = uid

    def resolve_user(self, name: str) -> str | None:
        with self._lock:
            return self.users_by_name.get(name)

    # ------------- OKE clusters -------------
    def update_clusters(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for c in items:
                cid = c.get("id") or c.get("_id")
                name = c.get("name") or c.get("_name") or c.get("display_name") or c.get("_display_name")
                if cid and name:
                    self.clusters_by_name[(compartment_id, name)] = cid

    def resolve_cluster(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.clusters_by_name.get((compartment_id, name))

    # ------------- Functions applications -------------
    def update_applications(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for a in items:
                aid = a.get("id") or a.get("_id")
                name = a.get("display_name") or a.get("_display_name") or a.get("name") or a.get("_name")
                if aid and name:
                    self.applications_by_name[(compartment_id, name)] = aid

    def resolve_application(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.applications_by_name.get((compartment_id, name))

    # ------------- Streaming streams -------------
    def update_streams(self, compartment_id: str, items: Iterable[dict]) -> None:
        with self._lock:
            for s in items:
                sid = s.get("id") or s.get("_id")
                name = s.get("name") or s.get("_name")
                if sid and name:
                    self.streams_by_name[(compartment_id, name)] = sid

    def resolve_stream(self, compartment_id: str, name: str) -> str | None:
        with self._lock:
            return self.streams_by_name.get((compartment_id, name))


_registry: NameRegistry | None = None


def get_registry() -> NameRegistry:
    global _registry
    if _registry is None:
        _registry = NameRegistry()
    return _registry
