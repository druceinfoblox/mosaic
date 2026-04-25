"""
Generates realistic synthetic DNS logs for demo purposes.
90 days of history, 200 clients across 4 subnets.
"""
import csv
import io
import random
from datetime import datetime, timedelta

SUBNETS = {
    "10.1.1": {"label": "Finance", "bu": "Finance"},
    "10.1.2": {"label": "Engineering", "bu": "Engineering"},
    "10.1.3": {"label": "HR", "bu": "Human Resources"},
    "10.1.4": {"label": "DataCenter", "bu": "IT Operations"},
}

INTERNAL_FQDNS = [
    "ad.corp.local",
    "dc01.corp.local",
    "dc02.corp.local",
    "erp.corp.local",
    "fileserver.corp.local",
    "fileserver02.corp.local",
    "ldap.corp.local",
    "smtp.corp.local",
    "intranet.corp.local",
    "wiki.corp.local",
    "jira.corp.internal",
    "confluence.corp.internal",
    "gitlab.corp.internal",
    "nexus.corp.internal",
    "jenkins.corp.internal",
    "grafana.corp.internal",
    "prometheus.corp.internal",
    "vault.corp.internal",
    "consul.corp.internal",
    "postgres01.corp.local",
    "postgres02.corp.local",
    "mysql01.corp.local",
    "redis01.corp.local",
    "kafka01.corp.local",
    "kafka02.corp.local",
    "elastic01.corp.local",
    "kibana.corp.local",
    "minio.corp.local",
    "backup.corp.local",
    "ntp.corp.local",
    "syslog.corp.local",
    "sccm.corp.local",
    "wsus.corp.local",
    "vcenter.corp.local",
    "esx01.corp.local",
    "esx02.corp.local",
    "netflow.corp.local",
    "snmp.corp.local",
    "tacacs.corp.local",
    "radius.corp.local",
    "hrms.corp.local",
    "payroll.corp.local",
    "erp-prod.corp.local",
    "erp-dev.corp.local",
    "sharepoint.corp.local",
    "exchange.corp.local",
    "sftp.corp.local",
    "vpn.corp.local",
    "proxy.corp.local",
    "loadbalancer.corp.local",
]

SAAS_FQDNS = [
    "login.salesforce.com",
    "mycompany.salesforce.com",
    "na1.salesforce.com",
    "outlook.office365.com",
    "login.microsoftonline.com",
    "teams.microsoft.com",
    "graph.microsoft.com",
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "app.slack.com",
    "xmpp.slack.com",
    "zoom.us",
    "api.zoom.us",
    "workday.com",
    "wd3.myworkday.com",
    "okta.com",
    "mycompany.okta.com",
    "crowdstrike.com",
    "falcon.crowdstrike.com",
    "zscaler.net",
    "gateway.zscaler.net",
    "s3.amazonaws.com",
    "ec2.amazonaws.com",
    "sts.amazonaws.com",
    "login.azure.com",
    "management.azure.com",
]

# Business-unit specific FQDN affinity
BU_FQDN_WEIGHTS = {
    "Finance": {
        "login.salesforce.com": 40, "mycompany.salesforce.com": 35,
        "erp.corp.local": 30, "payroll.corp.local": 25, "erp-prod.corp.local": 20,
        "ad.corp.local": 15, "outlook.office365.com": 20,
    },
    "Engineering": {
        "github.com": 45, "api.github.com": 35, "registry.npmjs.org": 30,
        "pypi.org": 25, "gitlab.corp.internal": 40, "jenkins.corp.internal": 30,
        "nexus.corp.internal": 25, "grafana.corp.internal": 20,
        "postgres01.corp.local": 15, "kafka01.corp.local": 15,
    },
    "Human Resources": {
        "workday.com": 45, "wd3.myworkday.com": 40, "payroll.corp.local": 35,
        "hrms.corp.local": 40, "mycompany.okta.com": 20, "sharepoint.corp.local": 15,
        "outlook.office365.com": 20,
    },
    "IT Operations": {
        "vcenter.corp.local": 40, "esx01.corp.local": 30, "esx02.corp.local": 30,
        "grafana.corp.internal": 35, "prometheus.corp.internal": 35,
        "consul.corp.internal": 25, "vault.corp.internal": 25,
        "elastic01.corp.local": 20, "kibana.corp.local": 20,
        "s3.amazonaws.com": 15, "ec2.amazonaws.com": 15,
    },
}

ANSWER_IPS = {
    **{f: [f"10.1.4.{i}" for i in range(10, 15)] for f in INTERNAL_FQDNS},
    "login.salesforce.com": ["136.147.57.42", "136.147.57.43"],
    "mycompany.salesforce.com": ["136.147.57.44"],
    "na1.salesforce.com": ["136.147.57.45"],
    "outlook.office365.com": ["52.96.10.1", "52.96.10.2"],
    "login.microsoftonline.com": ["20.190.128.1"],
    "teams.microsoft.com": ["52.113.194.1", "52.113.194.2"],
    "graph.microsoft.com": ["20.190.128.2"],
    "github.com": ["140.82.114.4", "140.82.114.3"],
    "api.github.com": ["140.82.114.5"],
    "raw.githubusercontent.com": ["185.199.108.133"],
    "registry.npmjs.org": ["104.16.91.158", "104.16.92.158"],
    "pypi.org": ["151.101.64.223"],
    "files.pythonhosted.org": ["151.101.64.224"],
    "app.slack.com": ["18.233.230.15", "18.233.230.16"],
    "xmpp.slack.com": ["18.233.230.17"],
    "zoom.us": ["170.114.52.1", "170.114.52.2"],
    "api.zoom.us": ["170.114.52.3"],
    "workday.com": ["205.175.245.100"],
    "wd3.myworkday.com": ["205.175.245.101"],
    "okta.com": ["104.72.164.1"],
    "mycompany.okta.com": ["104.72.164.2"],
    "crowdstrike.com": ["198.185.159.145"],
    "falcon.crowdstrike.com": ["198.185.159.146"],
    "zscaler.net": ["165.225.0.1"],
    "gateway.zscaler.net": ["165.225.0.2"],
    "s3.amazonaws.com": ["52.216.0.1", "54.231.0.1"],
    "ec2.amazonaws.com": ["52.0.0.1"],
    "sts.amazonaws.com": ["52.0.0.2"],
    "login.azure.com": ["40.126.32.1"],
    "management.azure.com": ["40.126.32.2"],
}

# Some ambiguous/noisy FQDNs
AMBIGUOUS_FQDNS = [
    "unknown-host.local",
    "192.168.1.1.in-addr.arpa",
    "wpad.corp.local",
    "isatap.corp.local",
    "teredo.ipv6.microsoft.com",
    "time.windows.com",
    "update.googleapis.com",
]

QTYPES = ["A", "A", "A", "A", "AAAA", "CNAME", "MX", "TXT"]
RCODES = ["NOERROR", "NOERROR", "NOERROR", "NOERROR", "NOERROR", "NXDOMAIN", "SERVFAIL"]


def generate_client_ips(n_per_subnet: int = 50) -> dict[str, str]:
    """Returns {ip: bu} mapping."""
    clients = {}
    for prefix, info in SUBNETS.items():
        for i in range(10, 10 + n_per_subnet):
            ip = f"{prefix}.{i}"
            clients[ip] = info["bu"]
    return clients


def _weighted_fqdn(bu: str, global_fqdns: list) -> str:
    weights = BU_FQDN_WEIGHTS.get(bu, {})
    pool = list(weights.keys()) + global_fqdns
    w = [weights.get(f, 1) for f in pool]
    return random.choices(pool, weights=w, k=1)[0]


def generate_events(days: int = 90, clients_per_subnet: int = 50) -> list[dict]:
    clients = generate_client_ips(clients_per_subnet)
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    events = []

    all_fqdns = INTERNAL_FQDNS + SAAS_FQDNS

    for client_ip, bu in clients.items():
        # Each client makes 20-200 queries per day on active days
        active_days = random.randint(days // 2, days)
        day_offsets = sorted(random.sample(range(days), k=min(active_days, days)))

        for day_offset in day_offsets:
            n_queries = random.randint(5, 80)
            for _ in range(n_queries):
                fqdn = _weighted_fqdn(bu, all_fqdns)
                # Occasional ambiguous/noisy entry
                if random.random() < 0.03:
                    fqdn = random.choice(AMBIGUOUS_FQDNS)

                ts = start + timedelta(
                    days=day_offset,
                    hours=random.randint(7, 20),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )
                rcode = random.choices(RCODES, weights=[70, 70, 70, 70, 70, 15, 5])[0]
                qtype = random.choices(QTYPES, weights=[60, 60, 60, 60, 10, 5, 5, 5])[0]
                answer_ips = ANSWER_IPS.get(fqdn, []) if rcode == "NOERROR" else []

                events.append({
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                    "client_ip": client_ip,
                    "fqdn": fqdn,
                    "qtype": qtype,
                    "rcode": rcode,
                    "answer_ips": ",".join(answer_ips),
                })

    random.shuffle(events)
    return events


def generate_csv(days: int = 90, clients_per_subnet: int = 50) -> str:
    events = generate_events(days, clients_per_subnet)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["timestamp", "client_ip", "fqdn", "qtype", "rcode", "answer_ips"])
    writer.writeheader()
    writer.writerows(events)
    return out.getvalue()


if __name__ == "__main__":
    import os
    out_path = os.path.join(os.path.dirname(__file__), "sample_dns_logs.csv")
    print(f"Generating sample DNS logs → {out_path}")
    data = generate_csv()
    with open(out_path, "w") as f:
        f.write(data)
    lines = data.count("\n")
    print(f"Generated {lines:,} log entries")
