"""
DNS log parser: supports CSV, JSON array, and syslog formats.
Auto-detects format from content.
"""
import csv
import json
import re
import io
from datetime import datetime
from typing import AsyncIterator
from app.schemas.dns_event import DnsEventCreate


TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y%m%d%H%M%S",
]

# Infoblox syslog pattern: client@port query: fqdn type class rcode
SYSLOG_PATTERN = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})"
    r".*?named.*?client\s+(?P<client>[\d.]+)#\d+.*?query:\s+(?P<fqdn>[\w.\-]+)"
    r"\s+(?P<cls>\w+)\s+(?P<qtype>\w+)\s+(?P<flags>[+\-RDE]*)"
    r"(?:\s+\((?P<answer>[^)]+)\))?",
    re.IGNORECASE,
)

SYSLOG_RESPONSE_PATTERN = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})"
    r".*?client\s+(?P<client>[\d.]+)#\d+.*?(?P<fqdn>[\w.\-]+)/(?P<qtype>\w+)/"
    r".*?->.*?(?P<rcode>NOERROR|NXDOMAIN|SERVFAIL|REFUSED)",
    re.IGNORECASE,
)


def _parse_timestamp(ts: str) -> datetime:
    ts = ts.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    # Fallback: attempt ISO fromisoformat
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
    except Exception:
        return datetime.utcnow()


def _parse_answer_ips(raw: str) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    parts = [p.strip() for p in re.split(r"[,;|\s]+", str(raw)) if p.strip()]
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return [p for p in parts if ip_pattern.match(p)]


def _detect_format(content: str) -> str:
    stripped = content.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return "json"
    # Try CSV by checking first line for known headers
    first_line = stripped.split("\n")[0].lower()
    csv_headers = {"timestamp", "client_ip", "fqdn", "qtype", "rcode"}
    if any(h in first_line for h in csv_headers):
        return "csv"
    # Check for syslog indicators
    if re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+", stripped, re.I):
        return "syslog"
    # Default to CSV if commas present
    if "," in first_line:
        return "csv"
    return "syslog"


def parse_csv(content: str) -> list[DnsEventCreate]:
    events = []
    reader = csv.DictReader(io.StringIO(content))
    # Normalize header names
    for row in reader:
        normalized = {k.strip().lower().replace(" ", "_"): v for k, v in row.items()}
        try:
            ts_raw = (
                normalized.get("timestamp")
                or normalized.get("time")
                or normalized.get("date")
                or ""
            )
            client_ip = (
                normalized.get("client_ip")
                or normalized.get("client")
                or normalized.get("src_ip")
                or ""
            ).strip()
            fqdn = (
                normalized.get("fqdn")
                or normalized.get("domain")
                or normalized.get("query")
                or normalized.get("name")
                or ""
            ).strip().rstrip(".")
            qtype = (normalized.get("qtype") or normalized.get("query_type") or "A").strip().upper()
            rcode = (normalized.get("rcode") or normalized.get("response_code") or "NOERROR").strip().upper()
            answers_raw = normalized.get("answer_ips") or normalized.get("answers") or normalized.get("answer") or ""

            if not client_ip or not fqdn:
                continue

            events.append(
                DnsEventCreate(
                    timestamp=_parse_timestamp(ts_raw),
                    client_ip=client_ip,
                    fqdn=fqdn,
                    query_type=qtype,
                    rcode=rcode,
                    answer_ips=_parse_answer_ips(answers_raw),
                    raw_line=str(row),
                )
            )
        except Exception:
            continue
    return events


def parse_json(content: str) -> list[DnsEventCreate]:
    events = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return events

    if isinstance(data, dict):
        data = data.get("records", data.get("events", data.get("logs", [data])))

    for record in data:
        if not isinstance(record, dict):
            continue
        try:
            ts_raw = (
                record.get("timestamp")
                or record.get("time")
                or record.get("@timestamp")
                or ""
            )
            client_ip = (
                record.get("client_ip")
                or record.get("client")
                or record.get("src_ip")
                or ""
            )
            fqdn = (
                record.get("fqdn")
                or record.get("domain")
                or record.get("query_name")
                or record.get("name")
                or ""
            ).rstrip(".")

            if not client_ip or not fqdn:
                continue

            events.append(
                DnsEventCreate(
                    timestamp=_parse_timestamp(str(ts_raw)),
                    client_ip=str(client_ip),
                    fqdn=fqdn,
                    query_type=str(record.get("qtype", record.get("query_type", "A"))).upper(),
                    rcode=str(record.get("rcode", "NOERROR")).upper(),
                    answer_ips=_parse_answer_ips(record.get("answer_ips", record.get("answers", []))),
                    raw_line=json.dumps(record),
                )
            )
        except Exception:
            continue
    return events


def parse_syslog(content: str) -> list[DnsEventCreate]:
    events = []
    current_year = datetime.utcnow().year
    for line in content.splitlines():
        if not line.strip():
            continue
        for pattern in (SYSLOG_PATTERN, SYSLOG_RESPONSE_PATTERN):
            m = pattern.search(line)
            if m:
                try:
                    groups = m.groupdict()
                    ts_str = f"{groups['month']} {groups['day']} {current_year} {groups['time']}"
                    ts = datetime.strptime(ts_str, "%b %d %Y %H:%M:%S")
                    events.append(
                        DnsEventCreate(
                            timestamp=ts,
                            client_ip=groups.get("client", "0.0.0.0"),
                            fqdn=groups.get("fqdn", "").rstrip("."),
                            query_type=groups.get("qtype", "A").upper(),
                            rcode=groups.get("rcode", "NOERROR").upper(),
                            answer_ips=_parse_answer_ips(groups.get("answer", "") or ""),
                            raw_line=line,
                        )
                    )
                except Exception:
                    pass
                break
    return events


def parse_dns_logs(content: str) -> list[DnsEventCreate]:
    fmt = _detect_format(content)
    if fmt == "json":
        return parse_json(content)
    elif fmt == "csv":
        return parse_csv(content)
    else:
        return parse_syslog(content)
