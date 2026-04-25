"""
Recommendation engine: generates Illumio object suggestions from DNS dependency data.
"""
from collections import defaultdict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.dependency import Dependency
from app.models.client_profile import ClientProfile
from app.models.fqdn_profile import FqdnProfile
from app.models.recommendation import Recommendation
from app.services.normalizer import is_private_ip


def _build_illumio_workload_group_payload(name: str, ips: list[str], labels: dict) -> dict:
    return {
        "object_type": "workload_group",
        "name": name,
        "description": f"Auto-discovered workload group from DNS analysis",
        "labels": [{"key": k, "value": v} for k, v in labels.items()],
        "unmanaged_workloads": [
            {"name": ip, "interfaces": [{"name": "eth0", "address": ip}], "labels": []}
            for ip in ips
        ],
    }


def _build_illumio_ip_list_payload(name: str, description: str, fqdn: str, answer_ips: list[str]) -> dict:
    ranges = [{"from_ip": ip} for ip in answer_ips[:50]] if answer_ips else []
    if fqdn and not ranges:
        ranges = [{"fqdn": fqdn}]
    return {
        "object_type": "ip_list",
        "name": name,
        "description": description,
        "ip_ranges": ranges,
        "fqdns": [{"fqdn": fqdn}] if fqdn else [],
    }


def _build_illumio_ruleset_payload(name: str, description: str, scope_labels: list) -> dict:
    return {
        "object_type": "ruleset",
        "name": name,
        "description": description,
        "scopes": [scope_labels],
        "rules": [],
    }


def _build_illumio_service_payload(name: str, description: str, ports: list[int]) -> dict:
    return {
        "object_type": "service",
        "name": name,
        "description": description,
        "service_ports": [{"port": p, "proto": 6} for p in ports],
    }


def _infer_ports_from_fqdn(fqdn: str) -> list[int]:
    fqdn_lower = fqdn.lower()
    if any(x in fqdn_lower for x in ("smtp", "mail", "_25")):
        return [25, 587, 465]
    if any(x in fqdn_lower for x in ("ldap", "_389")):
        return [389, 636]
    if any(x in fqdn_lower for x in ("_443", "https", "web", "www")):
        return [443]
    if any(x in fqdn_lower for x in ("_80", "http")):
        return [80]
    if "rdp" in fqdn_lower or "_3389" in fqdn_lower:
        return [3389]
    if "ssh" in fqdn_lower or "_22" in fqdn_lower:
        return [22]
    if "sql" in fqdn_lower or "db" in fqdn_lower or "postgres" in fqdn_lower:
        return [5432, 1433, 3306]
    return []


async def run_recommendations(db: AsyncSession) -> dict:
    # Clear existing
    await db.execute(delete(Recommendation))

    # Load data
    deps_result = await db.execute(select(Dependency))
    deps = deps_result.scalars().all()

    profiles_result = await db.execute(select(ClientProfile))
    profiles = {p.client_ip: p for p in profiles_result.scalars().all()}

    fqdns_result = await db.execute(select(FqdnProfile))
    fqdn_profiles = {f.fqdn: f for f in fqdns_result.scalars().all()}

    recommendations = []

    # ---- 1. WORKLOAD_GROUP recommendations ----
    # Group clients by (subnet, business_unit) then check top-5 FQDN overlap
    subnet_groups = defaultdict(list)
    for profile in profiles.values():
        key = (profile.subnet or profile.client_ip[:profile.client_ip.rfind(".")], profile.business_unit or "Unknown")
        subnet_groups[key].append(profile)

    for (subnet, bu), group_profiles in subnet_groups.items():
        if len(group_profiles) < 2:
            continue

        # Compute pairwise FQDN overlap
        top_fqdn_sets = [set(p.top_fqdns[:5]) for p in group_profiles]
        if not any(top_fqdn_sets):
            continue

        # Find consensus FQDNs (appear in >60% of members)
        all_fqdns = defaultdict(int)
        for fset in top_fqdn_sets:
            for f in fset:
                all_fqdns[f] += 1

        threshold = max(2, len(group_profiles) * 0.6)
        common_fqdns = [f for f, cnt in all_fqdns.items() if cnt >= threshold]

        if len(common_fqdns) < 2:
            continue

        ips = [p.client_ip for p in group_profiles]
        name = f"WG-{bu.replace(' ', '_')}-{subnet.split('/')[0].replace('.', '_')}"
        avg_confidence = sum(
            min(p.total_queries / 100, 1.0) * 0.5 for p in group_profiles
        ) / len(group_profiles)
        confidence = round(min(0.95, avg_confidence + 0.3), 4)

        labels = {}
        if bu and bu != "Unknown":
            labels["app"] = bu.lower().replace(" ", "-")
        if subnet:
            labels["env"] = "discovered"

        evidence = {
            "first_seen": min(p.first_seen for p in group_profiles if p.first_seen).isoformat() if any(p.first_seen for p in group_profiles) else None,
            "last_seen": max(p.last_seen for p in group_profiles if p.last_seen).isoformat() if any(p.last_seen for p in group_profiles) else None,
            "client_count": len(ips),
            "query_count": sum(p.total_queries for p in group_profiles),
            "top_fqdns": common_fqdns[:10],
            "confidence_score": confidence,
            "subnet": subnet,
            "business_unit": bu,
            "human_readable_reason": (
                f"{len(ips)} endpoints in {subnet} ({bu}) share DNS patterns to "
                f"{len(common_fqdns)} common destinations. High cohesion suggests shared workload role."
            ),
        }

        recommendations.append(
            Recommendation(
                type="WORKLOAD_GROUP",
                name=name,
                confidence=confidence,
                evidence=evidence,
                status="PENDING",
                illumio_payload=_build_illumio_workload_group_payload(name, ips, labels),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    # ---- 2. APP_DEPENDENCY recommendations (high confidence) ----
    high_conf = [d for d in deps if d.confidence_score > 0.7]
    # Group by fqdn
    fqdn_dep_groups = defaultdict(list)
    for d in high_conf:
        fqdn_dep_groups[d.fqdn].append(d)

    for fqdn, fqdn_deps in fqdn_dep_groups.items():
        if len(fqdn_deps) < 2:
            continue
        fqdn_profile = fqdn_profiles.get(fqdn)
        all_answer_ips = list(fqdn_profile.answer_ips) if fqdn_profile else []
        is_internal = all(is_private_ip(ip) for ip in all_answer_ips) if all_answer_ips else False

        avg_conf = sum(d.confidence_score for d in fqdn_deps) / len(fqdn_deps)
        total_queries = sum(d.query_count for d in fqdn_deps)
        client_ips = list({d.client_ip for d in fqdn_deps})
        all_first = [d.first_seen for d in fqdn_deps if d.first_seen]
        all_last = [d.last_seen for d in fqdn_deps if d.last_seen]

        name = f"DEP-{fqdn.replace('.', '_').replace('-', '_')[:40]}"
        evidence = {
            "first_seen": min(all_first).isoformat() if all_first else None,
            "last_seen": max(all_last).isoformat() if all_last else None,
            "client_count": len(client_ips),
            "query_count": total_queries,
            "days_observed": max(d.days_observed for d in fqdn_deps),
            "top_fqdns": [fqdn],
            "confidence_score": round(avg_conf, 4),
            "is_internal": is_internal,
            "answer_ips": all_answer_ips[:10],
            "human_readable_reason": (
                f"{len(client_ips)} workloads consistently query {fqdn} "
                f"({total_queries} total queries, avg confidence {avg_conf:.2f}). "
                f"Recommend as {'internal' if is_internal else 'external'} app dependency rule."
            ),
        }

        scope_labels = [{"key": "env", "value": "discovered"}]
        recommendations.append(
            Recommendation(
                type="APP_DEPENDENCY",
                name=name,
                confidence=round(avg_conf, 4),
                evidence=evidence,
                status="PENDING",
                illumio_payload=_build_illumio_ruleset_payload(name, f"Auto-generated ruleset for {fqdn}", scope_labels),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    # ---- 3. IP_LIST recommendations (external, high query count) ----
    external_fqdns = [
        f for f in fqdn_profiles.values()
        if not f.is_internal
        and f.total_queries > 50
        and f.answer_ips
    ]
    for fp in external_fqdns[:30]:  # Cap at 30 IP list recs
        name = f"IPL-{fp.fqdn.replace('.', '_').replace('-', '_')[:40]}"
        public_ips = [ip for ip in fp.answer_ips if not is_private_ip(ip)]
        if not public_ips and not fp.fqdn:
            continue

        evidence = {
            "first_seen": fp.first_seen.isoformat() if fp.first_seen else None,
            "last_seen": fp.last_seen.isoformat() if fp.last_seen else None,
            "client_count": fp.unique_clients,
            "query_count": fp.total_queries,
            "top_fqdns": [fp.fqdn],
            "confidence_score": round(min(fp.total_queries / 500, 1.0) * 0.8, 4),
            "is_external": True,
            "answer_ips": public_ips[:10],
            "human_readable_reason": (
                f"External FQDN {fp.fqdn} queried {fp.total_queries} times by "
                f"{fp.unique_clients} clients. Recommend as named IP list for policy reference."
            ),
        }

        confidence = round(min(fp.total_queries / 500, 1.0) * 0.8, 4)
        recommendations.append(
            Recommendation(
                type="IP_LIST",
                name=name,
                confidence=confidence,
                evidence=evidence,
                status="PENDING",
                illumio_payload=_build_illumio_ip_list_payload(
                    name,
                    f"Auto-discovered external destination: {fp.fqdn}",
                    fp.fqdn,
                    public_ips,
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    # ---- 4. SERVICE recommendations ----
    service_fqdns = [f for f in fqdn_profiles.values() if _infer_ports_from_fqdn(f.fqdn)]
    for fp in service_fqdns[:20]:
        ports = _infer_ports_from_fqdn(fp.fqdn)
        name = f"SVC-{fp.fqdn.split('.')[0].upper()[:20]}-{ports[0]}"
        evidence = {
            "first_seen": fp.first_seen.isoformat() if fp.first_seen else None,
            "last_seen": fp.last_seen.isoformat() if fp.last_seen else None,
            "client_count": fp.unique_clients,
            "query_count": fp.total_queries,
            "top_fqdns": [fp.fqdn],
            "confidence_score": 0.65,
            "inferred_ports": ports,
            "human_readable_reason": (
                f"FQDN {fp.fqdn} suggests service on port(s) {ports}. "
                f"Recommend as named service object for policy reuse."
            ),
        }
        recommendations.append(
            Recommendation(
                type="SERVICE",
                name=name,
                confidence=0.65,
                evidence=evidence,
                status="PENDING",
                illumio_payload=_build_illumio_service_payload(name, f"Service for {fp.fqdn}", ports),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    db.add_all(recommendations)
    await db.commit()

    type_counts = defaultdict(int)
    for r in recommendations:
        type_counts[r.type] += 1

    return {
        "total": len(recommendations),
        "by_type": dict(type_counts),
    }
