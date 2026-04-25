# Project Mosaic — 15-Minute Customer Demo Script

**Audience:** Security architect or network security lead  
**Setup:** `docker compose up` already running, browser open to http://localhost:4173  
**Story:** "Your Infoblox DNS history already contains the answer to your microsegmentation project — Mosaic extracts it automatically."

---

## Part 1: The Problem (1 min)

> "Microsegmentation projects fail because of the discovery phase. Your team spends months manually interviewing app owners, chasing runbooks, and drawing dependency maps that are out of date by the time you finish. Mosaic solves this."

---

## Part 2: Overview Page — The Numbers (3 min)

**Navigate to: Overview (`/`)**

1. Click **"Generate Demo Data"** — this simulates 90 days of DNS logs from 200 endpoints across 4 business units (Finance, Engineering, HR, IT Ops).

2. Watch the KPI tiles populate:
   - **DNS Events** — ~15,000 log lines ingested in seconds
   - **Unique Endpoints** — 200 workloads discovered automatically
   - **Unique FQDNs** — 120+ destinations mapped
   - **App Dependencies** — 45+ candidate application flows
   - **Network Segments** — 8 proposed microsegment boundaries
   - **Draft Illumio Objects** — 120 policy objects ready for review
   - **Weeks Saved** — estimated 6 weeks vs. manual discovery

> "In the time it took to load this page, Mosaic processed 90 days of DNS history and identified 120 candidate policy objects. Your team would have spent 6 weeks doing this manually."

---

## Part 3: Dependency Explorer — The Evidence (3 min)

**Navigate to: Dependency Explorer (`/explorer`)**

1. Point out the **bar chart** at the top — colored by destination type:
   - **Green** = internal corp infrastructure
   - **Blue** = SaaS/external services
   - **Orange** = ambiguous (needs human review)

2. Scroll through the **dependency table**. Highlight:
   - High-confidence Finance group querying Salesforce daily
   - Engineering group with consistent npm/PyPI/GitHub patterns
   - HR group traffic to Workday/Okta
   - Internal AD/LDAP queries shared across all subnets

3. Set the **Min Confidence** slider to 70%:
   > "These are dependencies with 30+ days of consistent evidence and stable answer IPs. Zero manual validation needed."

4. Click a client IP — shows the WorkloadDetail page with:
   - FQDN breakdown chart for that specific endpoint
   - RCODE distribution (NOERROR vs NXDOMAIN for anomaly hunting)
   - Query timeline

---

## Part 4: Recommendation Workbench — The Policy Objects (4 min)

**Navigate to: Recommendations (`/recommendations`)**

1. Show the four **recommendation types**:
   - **WORKLOAD_GROUP** (purple) — clusters of endpoints with shared DNS behavior
   - **APP_DEPENDENCY** (blue) — high-confidence client→FQDN rules
   - **IP_LIST** (teal) — external services as named IP lists
   - **SERVICE** (orange) — port inference from FQDN keywords

2. Filter by **WORKLOAD_GROUP**:
   > "Mosaic found that all Finance IPs on 10.1.1.0/24 share the same DNS destinations — Salesforce, ERP, payroll. That's a natural microsegment."

3. Click the **expand arrow** on a WORKLOAD_GROUP:
   - Show the `human_readable_reason` field: plain English explanation of the evidence
   - Point out client count, query count, days observed
   > "Every recommendation comes with audit-ready evidence. Your Change Advisory Board can see exactly why each object was created."

4. Click **Approve** on 3-4 high-confidence recommendations.

5. Filter by **SERVICE**:
   > "Mosaic also inferred services — it saw queries to smtp.corp.local and automatically proposed a named TCP/25/587 service object. Port inference from DNS keywords."

---

## Part 5: Ambiguity Queue — Human-in-the-Loop (1 min)

**Navigate to: Ambiguity Queue (`/ambiguity`)**

> "Not everything gets auto-approved. Low-confidence items — things seen only once or twice, or with inconsistent answer IPs — land here for human review. You're in control."

Show a few items and click Approve/Reject to demonstrate the workflow.

---

## Part 6: Publish to Illumio — The Payoff (3 min)

**Navigate to: Publish (`/publish`)**

1. Point out the **left panel** — all approved recommendations.

2. Click each one — the **right panel** shows the exact JSON payload:
   - For WORKLOAD_GROUP: unmanaged workload list with eth0 interfaces and labels
   - For IP_LIST: ip_ranges with `from_ip` entries
   - For SERVICE: service_ports with port + proto
   - For APP_DEPENDENCY: ruleset with scope labels

3. Toggle **Dry Run** (enabled by default):
   > "Dry run means we generate and preview every payload but don't commit anything to the PCE. You get to see exactly what will happen."

4. Click **Preview Push**:
   > "Each object is individually validated. You get back a result per recommendation — success, failure, or simulation. Full audit trail."

5. If PCE is connected, toggle Dry Run **off** and click **Push to PCE**:
   > "These objects land in PCE as drafts. Your team reviews them in the PCE UI before provisioning. Mosaic hands off clean, structured objects — you still control the final policy decision."

---

## Close (1 min)

> "To summarize what just happened: we ingested 90 days of DNS history, discovered 200 workloads, mapped their application dependencies, generated 120 policy object candidates with full audit evidence, and pushed them to Illumio PCE as drafts — in under 5 minutes. With your real DNS logs, this becomes your microsegmentation starting point, not your final project."

**Questions?**

---

## Setup Checklist

- [ ] `docker compose up --build` complete
- [ ] http://localhost:4173 loads
- [ ] http://localhost:8000/docs accessible
- [ ] (Optional) .env configured with PCE credentials for live push demo
