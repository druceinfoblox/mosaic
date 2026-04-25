# Project Mosaic

**DNS history → microsegmentation policy in minutes, not months.**

Mosaic ingests Infoblox DNS query logs, discovers application dependencies through behavioral analysis, and automatically generates Illumio PCE policy object recommendations — workload groups, app dependency rules, IP lists, and named services.

## Architecture

```
DNS Logs (CSV / JSON / Syslog)
        │
        ▼
  Ingest & Parse ──────────────────── DnsEvent table
        │
        ▼
  Correlation ─────────────────────── ClientProfile
  (per-IP, per-FQDN)                  FqdnProfile
  confidence scoring                  Dependency
        │
        ▼
  Enrichment ──────────────────────── SubnetContext lookup
  (subnet → BU / owner / site)        enriches ClientProfile
        │
        ▼
  Recommendation Engine ───────────── Recommendation table
  WORKLOAD_GROUP | APP_DEPENDENCY     (PENDING -> review)
  IP_LIST        | SERVICE
        │
        ▼
  Review Workbench ────────────────── Approve / Reject
  + Ambiguity Queue
        │
        ▼
  Illumio Publish ─────────────────── PCE API (or dry-run)
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your Illumio PCE credentials (optional — demo mode works without them)

# 2. Start services
docker compose up --build

# 3. Open the UI
open http://localhost:4173

# 4. Generate demo data (in the Overview page) or upload your DNS logs
```

**Backend API docs:** http://localhost:8000/docs

## Services

| Service  | Port | Description              |
|----------|------|--------------------------|
| backend  | 8000 | FastAPI + SQLite         |
| frontend | 4173 | Vite React SPA via nginx |

## Demo Flow

1. **Overview** — Click "Generate Demo Data" to load 90 days of synthetic DNS logs
2. **Dependency Explorer** — Browse client->FQDN relationships, filter by confidence
3. **Recommendations** — Approve high-confidence Illumio policy objects
4. **Publish** — Preview JSON payloads, dry-run push to Illumio PCE

## Configuration

| Variable                   | Default | Description                  |
|----------------------------|---------|------------------------------|
| `ILLUMIO_PCE_URL`          | —       | PCE base URL                 |
| `ILLUMIO_ORG_ID`           | `1`     | PCE organization ID          |
| `ILLUMIO_API_KEY_USERNAME` | —       | API key username             |
| `ILLUMIO_API_KEY_SECRET`   | —       | API key secret               |
| `ILLUMIO_DRY_RUN`          | `true`  | Simulate PCE writes          |
| `DATA_DIR`                 | `/data` | SQLite DB and data directory |

## Uploading Real DNS Logs

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@your-dns-logs.csv"
```

Supported formats:
- **CSV** — `timestamp, client_ip, fqdn, qtype, rcode, answer_ips`
- **JSON** — array of records or `{"records": [...]}`
- **Syslog** — Infoblox named syslog format

After uploading, click **Run Analysis** in the Overview page (or `POST /api/v1/analyze`).

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Limitations

- SQLite is used for simplicity; swap in Postgres for production scale
- DNS-based dependency discovery cannot see encrypted-SNI or IP-direct connections
- Confidence scoring is heuristic; review ambiguous items in the Ambiguity Queue
- Illumio integration requires PCE 22.2+ with REST API enabled
- Demo data is synthetic — real DNS logs will show more nuanced patterns
