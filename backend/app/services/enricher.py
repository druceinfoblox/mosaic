"""
Enriches client_profiles with subnet context (owner, BU, site).
"""
import ipaddress
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.client_profile import ClientProfile
from app.models.subnet_context import SubnetContext

logger = logging.getLogger(__name__)


async def run_enrichment(db: AsyncSession) -> dict:
    # Load all subnet contexts
    result = await db.execute(select(SubnetContext))
    subnet_entries = result.scalars().all()

    if not subnet_entries:
        logger.info("No subnet context entries found; skipping CIDR enrichment")
        # Still do /24 grouping fallback
        return await _enrich_with_fallback(db)

    # Build list of (network, context) sorted by prefix length (most specific first)
    networks = []
    for entry in subnet_entries:
        try:
            net = ipaddress.ip_network(entry.cidr, strict=False)
            networks.append((net, entry))
        except ValueError:
            logger.warning(f"Invalid CIDR {entry.cidr}, skipping")

    networks.sort(key=lambda x: x[0].prefixlen, reverse=True)

    # Enrich client profiles
    result = await db.execute(select(ClientProfile))
    profiles = result.scalars().all()
    enriched = 0

    for profile in profiles:
        try:
            client_addr = ipaddress.ip_address(profile.client_ip)
        except ValueError:
            continue

        matched = None
        for net, ctx in networks:
            if client_addr in net:
                matched = ctx
                break

        if matched:
            profile.subnet = matched.cidr
            profile.owner = matched.owner
            profile.site = matched.site
            profile.business_unit = matched.business_unit
            enriched += 1
        else:
            # Fallback: /24 subnet label
            parts = profile.client_ip.split(".")
            if len(parts) == 4:
                profile.subnet = f"{'.'.join(parts[:3])}.0/24"

    await db.commit()

    # WAPI stub
    logger.info("WAPI not configured — skipping IPAM enrichment")

    return {"enriched": enriched, "total": len(profiles)}


async def _enrich_with_fallback(db: AsyncSession) -> dict:
    result = await db.execute(select(ClientProfile))
    profiles = result.scalars().all()
    for profile in profiles:
        parts = profile.client_ip.split(".")
        if len(parts) == 4 and not profile.subnet:
            profile.subnet = f"{'.'.join(parts[:3])}.0/24"
    await db.commit()
    return {"enriched": 0, "total": len(profiles), "fallback": "cidr_24"}


async def seed_demo_subnet_context(db: AsyncSession) -> None:
    """Insert demo subnet context if table is empty."""
    result = await db.execute(select(SubnetContext))
    if result.scalars().first():
        return

    demo_subnets = [
        SubnetContext(cidr="10.1.1.0/24", label="Finance", business_unit="Finance", site="HQ", owner="finance-team"),
        SubnetContext(cidr="10.1.2.0/24", label="Engineering", business_unit="Engineering", site="HQ", owner="eng-team"),
        SubnetContext(cidr="10.1.3.0/24", label="HR", business_unit="Human Resources", site="HQ", owner="hr-team"),
        SubnetContext(cidr="10.1.4.0/24", label="DataCenter", business_unit="IT Operations", site="DC1", owner="ops-team"),
    ]
    db.add_all(demo_subnets)
    await db.commit()
