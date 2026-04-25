# Project Mosaic — Architecture

## System Overview

```mermaid
graph TB
    subgraph Input["Data Sources"]
        A[DNS Logs - CSV]
        B[DNS Logs - JSON]
        C[DNS Logs - Syslog]
        D[Subnet Context CSV]
    end

    subgraph Ingest["Ingest Layer"]
        E[Parser Service\nauto-detect format\ntimestamp normalization]
        F[Normalizer\nbulk insert\ndedup]
    end

    subgraph Storage["SQLite Database"]
        G[(DnsEvent\nclient_ip · fqdn · rcode\nanswer_ips · timestamp)]
        H[(SubnetContext\ncidr · owner · BU · site)]
    end

    subgraph Analysis["Analysis Pipeline"]
        I[Correlator\nbuild dependency matrix\nconfidence scoring]
        J[Enricher\nsubnet → BU/owner\nContext enrichment]
        K[Recommender\nWORKLOAD_GROUP\nAPP_DEPENDENCY\nIP_LIST · SERVICE]
    end

    subgraph Derived["Derived Tables"]
        L[(ClientProfile\nper-IP stats\nBU · subnet · owner)]
        M[(FqdnProfile\nper-FQDN stats\ncategory · answer_ips)]
        N[(Dependency\nclient_ip · fqdn\nconfidence_score)]
        O[(Recommendation\ntype · status\nillumio_payload)]
    end

    subgraph API["FastAPI Backend :8000"]
        P[/api/v1/ingest]
        Q[/api/v1/analyze]
        R[/api/v1/dependencies]
        S[/api/v1/workloads]
        T[/api/v1/recommendations]
        U[/api/v1/illumio/push]
    end

    subgraph Frontend["React Frontend :4173"]
        V[Overview Page\nKPI Dashboard]
        W[Dependency Explorer\nMatrix + Charts]
        X[Recommendation Workbench\nApprove / Reject]
        Y[Workload Detail\nPer-IP Analysis]
        Z[Illumio Publish\nJSON Preview + Push]
        AA[Ambiguity Queue\nHuman Review]
    end

    subgraph PCE["Illumio PCE"]
        BB[Workload Groups]
        CC[IP Lists]
        DD[Services]
        EE[Rulesets]
    end

    A --> E
    B --> E
    C --> E
    D --> H
    E --> F
    F --> G
    G --> I
    H --> J
    I --> L
    I --> M
    I --> N
    J --> L
    N --> K
    L --> K
    M --> K
    K --> O
    G --> P
    L --> S
    M --> R
    N --> R
    O --> T
    P --> API
    Q --> Analysis
    R --> Frontend
    S --> Frontend
    T --> Frontend
    U --> PCE
    V --> Q
    X --> T
    Z --> U
    BB --> PCE
    CC --> PCE
    DD --> PCE
    EE --> PCE
```

## Confidence Scoring

Dependencies are scored on three factors, weighted by reliability:

| Factor      | Weight | Formula                              |
|-------------|--------|--------------------------------------|
| Temporal    | 50%    | `min(days_observed / 30, 1.0)`       |
| Volume      | 30%    | `min(query_count / 100, 1.0)`        |
| Stability   | 20%    | `1.0 if answer_ips_stable else 0.0`  |

**Confidence = 0.5×time + 0.3×volume + 0.2×stability**

Items scoring ≥ 0.7 are eligible for automatic recommendation. Items < 0.6 land in the Ambiguity Queue.

## Recommendation Types

| Type             | Trigger Condition                                        | Illumio Object |
|------------------|----------------------------------------------------------|----------------|
| `WORKLOAD_GROUP` | 2+ clients share 60%+ of top-5 FQDNs in same subnet/BU  | Unmanaged Workload Group |
| `APP_DEPENDENCY` | FQDN queried by 2+ clients with confidence > 0.7         | Ruleset (draft rules) |
| `IP_LIST`        | External FQDN with 50+ queries and known answer IPs      | IP List |
| `SERVICE`        | FQDN keyword implies port (smtp/ldap/ssh/rdp/sql/web)    | Service |

## FQDN Categorization

```
.local / .corp / .internal / .lan → "internal"
salesforce / workday / okta / slack / zoom → "saas-*"
github / npm / pypi / gitlab → "saas-devtools"
aws / azure / gcp → "cloud-infra"
everything else → "external"
```

## Data Flow

```
POST /ingest (file upload)
    → parser.parse_dns_logs()         # auto-detect CSV/JSON/syslog
    → normalizer.bulk_insert_events() # upsert into DnsEvent

POST /analyze
    → correlator.run_correlation()    # build Dependency matrix, ClientProfile, FqdnProfile
    → enricher.run_enrichment()       # match IPs to SubnetContext CIDR ranges
    → recommender.run_recommendations() # generate 4 object types into Recommendation

PATCH /recommendations/{id}           # approve / reject
POST /illumio/push?dry_run=true       # serialize payloads → PCE or dry-run preview
```

## Technology Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python 3.11, FastAPI, SQLAlchemy 2  |
| Database     | SQLite + aiosqlite (async)          |
| Frontend     | React 18, TypeScript, Vite, Tailwind CSS |
| Charts       | Recharts                            |
| HTTP client  | Axios                               |
| Icons        | Lucide React                        |
| Container    | Docker, nginx (frontend), uvicorn   |
| Illumio API  | REST v2, Basic Auth, PCE 22.2+      |
