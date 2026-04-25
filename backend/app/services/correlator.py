"""
Builds client_profiles, fqdn_profiles, and dependencies from dns_events.
"""
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from app.models.dns_event import DnsEvent
from app.models.client_profile import ClientProfile
from app.models.fqdn_profile import FqdnProfile
from app.models.dependency import Dependency
from app.services.normalizer import is_private_ip


def _compute_confidence(days_observed: int, query_count: int, answer_ips_stable: bool) -> float:
    time_score = min(days_observed / 30.0, 1.0) * 0.5
    volume_score = min(query_count / 100.0, 1.0) * 0.3
    stability_score = 0.2 if answer_ips_stable else 0.0
    return round(time_score + volume_score + stability_score, 4)


async def run_correlation(db: AsyncSession) -> dict:
    # Fetch all events
    result = await db.execute(select(DnsEvent))
    events = result.scalars().all()

    if not events:
        return {"message": "No events to correlate", "dependencies": 0}

    # --- Build dependency structures ---
    dep_key = {}  # (client_ip, fqdn) -> {first, last, dates, count, answer_ips_sets}
    client_data = defaultdict(lambda: {"fqdns": set(), "count": 0, "first": None, "last": None})
    fqdn_data = defaultdict(lambda: {"clients": set(), "count": 0, "first": None, "last": None, "ips": set()})

    for ev in events:
        key = (ev.client_ip, ev.fqdn)
        ts = ev.timestamp
        ips = frozenset(ev.answer_ips or [])

        if key not in dep_key:
            dep_key[key] = {
                "first": ts,
                "last": ts,
                "dates": set(),
                "count": 0,
                "answer_ip_sets": [],
            }
        d = dep_key[key]
        if ts < d["first"]:
            d["first"] = ts
        if ts > d["last"]:
            d["last"] = ts
        d["dates"].add(ts.date())
        d["count"] += 1
        d["answer_ip_sets"].append(ips)

        # client aggregation
        cd = client_data[ev.client_ip]
        cd["fqdns"].add(ev.fqdn)
        cd["count"] += 1
        if cd["first"] is None or ts < cd["first"]:
            cd["first"] = ts
        if cd["last"] is None or ts > cd["last"]:
            cd["last"] = ts

        # fqdn aggregation
        fd = fqdn_data[ev.fqdn]
        fd["clients"].add(ev.client_ip)
        fd["count"] += 1
        if fd["first"] is None or ts < fd["first"]:
            fd["first"] = ts
        if fd["last"] is None or ts > fd["last"]:
            fd["last"] = ts
        for ip in ev.answer_ips or []:
            fd["ips"].add(ip)

    # --- Clear and rebuild profiles ---
    await db.execute(delete(Dependency))
    await db.execute(delete(ClientProfile))
    await db.execute(delete(FqdnProfile))

    # Build dependency rows
    dep_rows = []
    for (client_ip, fqdn), d in dep_key.items():
        days_observed = len(d["dates"])
        query_count = d["count"]
        # Stability: all answer IP sets are the same
        unique_ip_sets = set(d["answer_ip_sets"])
        stable = len(unique_ip_sets) == 1

        # Determine if target is internal
        all_ips = list(d["answer_ip_sets"][-1]) if d["answer_ip_sets"] else []
        is_internal = all(is_private_ip(ip) for ip in all_ips) if all_ips else False

        confidence = _compute_confidence(days_observed, query_count, stable)
        dep_rows.append(
            Dependency(
                client_ip=client_ip,
                fqdn=fqdn,
                first_seen=d["first"],
                last_seen=d["last"],
                query_count=query_count,
                days_observed=days_observed,
                confidence_score=confidence,
                is_internal=is_internal,
                answer_ips_stable=stable,
                updated_at=datetime.utcnow(),
            )
        )

    # Build client profile rows
    client_rows = []
    for client_ip, cd in client_data.items():
        # Top fqdns by query count for this client
        fqdn_counts = defaultdict(int)
        for ev in events:
            if ev.client_ip == client_ip:
                fqdn_counts[ev.fqdn] += 1
        top_fqdns = sorted(fqdn_counts, key=fqdn_counts.get, reverse=True)[:10]
        client_rows.append(
            ClientProfile(
                client_ip=client_ip,
                first_seen=cd["first"],
                last_seen=cd["last"],
                total_queries=cd["count"],
                unique_fqdns=len(cd["fqdns"]),
                top_fqdns=top_fqdns,
                updated_at=datetime.utcnow(),
            )
        )

    # Build FQDN profile rows
    fqdn_rows = []
    for fqdn, fd in fqdn_data.items():
        all_ips = list(fd["ips"])
        is_internal = all(is_private_ip(ip) for ip in all_ips) if all_ips else False
        fqdn_rows.append(
            FqdnProfile(
                fqdn=fqdn,
                first_seen=fd["first"],
                last_seen=fd["last"],
                total_queries=fd["count"],
                unique_clients=len(fd["clients"]),
                answer_ips=all_ips[:20],
                is_internal=is_internal,
                category=_categorize_fqdn(fqdn),
                updated_at=datetime.utcnow(),
            )
        )

    db.add_all(dep_rows)
    db.add_all(client_rows)
    db.add_all(fqdn_rows)
    await db.commit()

    return {
        "dependencies": len(dep_rows),
        "client_profiles": len(client_rows),
        "fqdn_profiles": len(fqdn_rows),
    }


def _categorize_fqdn(fqdn: str) -> str:
    fqdn_lower = fqdn.lower()
    internal_tlds = (".local", ".corp", ".internal", ".lan", ".home")
    saas_keywords = {
        "salesforce": "saas-crm",
        "office365": "saas-productivity",
        "microsoft": "saas-productivity",
        "google": "saas-productivity",
        "github": "saas-devtools",
        "slack": "saas-communication",
        "zoom": "saas-communication",
        "workday": "saas-hr",
        "okta": "saas-identity",
        "crowdstrike": "saas-security",
        "zscaler": "saas-security",
        "aws": "cloud-infra",
        "azure": "cloud-infra",
        "gcp": "cloud-infra",
        "npm": "saas-devtools",
        "pypi": "saas-devtools",
    }
    if any(fqdn_lower.endswith(tld) for tld in internal_tlds):
        return "internal"
    for keyword, category in saas_keywords.items():
        if keyword in fqdn_lower:
            return category
    return "external"
