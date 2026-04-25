"""
Illumio PCE adapter. All write operations support dry_run=True (default).
"""
import asyncio
import logging
import time
from typing import Optional
import aiohttp
from aiohttp import BasicAuth

logger = logging.getLogger(__name__)


class IllumioClient:
    def __init__(
        self,
        pce_url: str,
        org_id: int,
        api_key_username: str,
        api_key_secret: str,
        dry_run: bool = True,
    ):
        self.pce_url = pce_url.rstrip("/")
        self.org_id = org_id
        self.api_key_username = api_key_username
        self.api_key_secret = api_key_secret
        self.dry_run = dry_run
        self._auth = BasicAuth(api_key_username, api_key_secret)
        self._request_times: list[float] = []
        self._rate_limit = 490  # per minute

    def _api_url(self, path: str) -> str:
        return f"{self.pce_url}/api/v2/orgs/{self.org_id}/{path.lstrip('/')}"

    async def _rate_check(self) -> None:
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < 60]
        if len(self._request_times) >= self._rate_limit:
            wait = 60 - (now - self._request_times[0]) + 1
            logger.warning(f"Rate limit approaching, backing off {wait:.1f}s")
            await asyncio.sleep(wait)
        self._request_times.append(time.monotonic())

    async def _request(self, method: str, path: str, json: Optional[dict] = None) -> dict:
        await self._rate_check()
        url = self._api_url(path)
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(method, url, json=json, auth=self._auth, ssl=False) as resp:
                request_id = resp.headers.get("X-Request-Id", "N/A")
                logger.info(f"{method} {url} -> {resp.status} X-Request-Id={request_id}")
                resp.raise_for_status()
                try:
                    return await resp.json()
                except Exception:
                    return {"status": resp.status}

    async def test_connection(self) -> dict:
        try:
            result = await self._request("GET", "labels?max_results=1")
            return {"connected": True, "pce_url": self.pce_url, "org_id": self.org_id}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def get_workloads(self, max_results: int = 500) -> list:
        return await self._request("GET", f"workloads?max_results={max_results}")

    async def get_labels(self) -> list:
        return await self._request("GET", "labels")

    async def create_label(self, key: str, value: str) -> dict:
        if self.dry_run:
            return {"dry_run": True, "key": key, "value": value}
        return await self._request("POST", "labels", json={"key": key, "value": value})

    async def create_unmanaged_workload(self, name: str, interfaces: list, labels: list) -> dict:
        payload = {
            "name": name,
            "interfaces": interfaces,
            "labels": labels,
            "enforcement_mode": "visibility_only",
        }
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        return await self._request("POST", "workloads", json=payload)

    async def create_ip_list_draft(self, name: str, description: str, ranges: list) -> dict:
        payload = {"name": name, "description": description, "ip_ranges": ranges}
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        return await self._request("POST", "sec_policy/draft/ip_lists", json=payload)

    async def create_service_draft(self, name: str, description: str, service_ports: list) -> dict:
        payload = {"name": name, "description": description, "service_ports": service_ports}
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        return await self._request("POST", "sec_policy/draft/services", json=payload)

    async def create_ruleset_draft(self, name: str, description: str, scopes: list) -> dict:
        payload = {"name": name, "description": description, "scopes": scopes}
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        return await self._request("POST", "sec_policy/draft/rule_sets", json=payload)

    async def create_rule_draft(
        self, ruleset_href: str, providers: list, consumers: list, services: list
    ) -> dict:
        payload = {
            "providers": providers,
            "consumers": consumers,
            "ingress_services": services,
            "resolve_labels_as": {"providers": ["workloads"], "consumers": ["workloads"]},
        }
        if self.dry_run:
            return {"dry_run": True, "ruleset_href": ruleset_href, "payload": payload}
        path = f"sec_policy/draft/rule_sets/{ruleset_href.split('/')[-1]}/sec_rules"
        return await self._request("POST", path, json=payload)

    async def bulk_create_labels(self, labels: list) -> list:
        results = []
        for lbl in labels:
            result = await self.create_label(lbl["key"], lbl["value"])
            results.append(result)
        return results


def get_illumio_client(settings: dict, dry_run: bool = True) -> Optional["IllumioClient"]:
    pce_url = settings.get("ILLUMIO_PCE_URL", "")
    if not pce_url or pce_url == "https://your-pce.illumio.com":
        return None
    return IllumioClient(
        pce_url=pce_url,
        org_id=int(settings.get("ILLUMIO_ORG_ID", 1)),
        api_key_username=settings.get("ILLUMIO_API_KEY_USERNAME", ""),
        api_key_secret=settings.get("ILLUMIO_API_KEY_SECRET", ""),
        dry_run=dry_run,
    )
