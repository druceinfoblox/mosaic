"""Tests for recommendation engine — confidence scoring and payload builders."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.correlator import _compute_confidence
from app.services.recommender import (
    _build_illumio_workload_group_payload,
    _build_illumio_ip_list_payload,
    _build_illumio_service_payload,
    _build_illumio_ruleset_payload,
    _infer_ports_from_fqdn,
)


class TestComputeConfidence:
    def test_max_all_factors(self):
        conf = _compute_confidence(days_observed=30, query_count=100, answer_ips_stable=True)
        assert conf == pytest.approx(1.0)

    def test_zero_everything(self):
        conf = _compute_confidence(days_observed=0, query_count=0, answer_ips_stable=False)
        assert conf == pytest.approx(0.0)

    def test_time_component_half(self):
        # 15/30 days → 0.5 * 0.5 = 0.25
        conf = _compute_confidence(days_observed=15, query_count=0, answer_ips_stable=False)
        assert conf == pytest.approx(0.25)

    def test_time_capped_at_30_days(self):
        conf_30 = _compute_confidence(days_observed=30, query_count=0, answer_ips_stable=False)
        conf_90 = _compute_confidence(days_observed=90, query_count=0, answer_ips_stable=False)
        assert conf_30 == conf_90

    def test_volume_component_full(self):
        # 100 queries → 1.0 * 0.3 = 0.3
        conf = _compute_confidence(days_observed=0, query_count=100, answer_ips_stable=False)
        assert conf == pytest.approx(0.3)

    def test_volume_capped_at_100_queries(self):
        conf_100 = _compute_confidence(days_observed=0, query_count=100, answer_ips_stable=False)
        conf_500 = _compute_confidence(days_observed=0, query_count=500, answer_ips_stable=False)
        assert conf_100 == conf_500

    def test_stability_bonus(self):
        unstable = _compute_confidence(days_observed=0, query_count=0, answer_ips_stable=False)
        stable = _compute_confidence(days_observed=0, query_count=0, answer_ips_stable=True)
        assert stable - unstable == pytest.approx(0.2)

    def test_high_confidence_combination(self):
        # 30 days + 100 queries + stable = 1.0
        conf = _compute_confidence(30, 100, True)
        assert conf >= 0.9

    def test_low_confidence_new_noisy_unstable(self):
        conf = _compute_confidence(days_observed=1, query_count=5, answer_ips_stable=False)
        assert conf < 0.2

    def test_result_is_rounded(self):
        conf = _compute_confidence(7, 33, True)
        # Should be rounded to 4 decimal places
        assert len(str(conf).rstrip("0").split(".")[-1]) <= 4


class TestInferPorts:
    def test_smtp_fqdn(self):
        ports = _infer_ports_from_fqdn("smtp.company.com")
        assert 25 in ports and 587 in ports

    def test_ldap_fqdn(self):
        ports = _infer_ports_from_fqdn("ldap.corp.local")
        assert 389 in ports

    def test_ssh_fqdn(self):
        assert 22 in _infer_ports_from_fqdn("ssh.bastion.corp.local")

    def test_rdp_fqdn(self):
        assert 3389 in _infer_ports_from_fqdn("rdp.desktops.corp")

    def test_sql_fqdn(self):
        ports = _infer_ports_from_fqdn("sql01.database.corp.local")
        assert any(p in ports for p in [5432, 1433, 3306])

    def test_https_fqdn(self):
        assert 443 in _infer_ports_from_fqdn("web.internal.corp")

    def test_generic_returns_empty(self):
        assert _infer_ports_from_fqdn("github.com") == []
        assert _infer_ports_from_fqdn("ad.corp.local") == []


class TestBuildWorkloadGroupPayload:
    def test_required_keys_present(self):
        payload = _build_illumio_workload_group_payload(
            "WG-Finance", ["10.1.1.1", "10.1.1.2"],
            {"app": "finance", "env": "discovered"},
        )
        for key in ("object_type", "name", "description", "labels", "unmanaged_workloads"):
            assert key in payload

    def test_object_type(self):
        payload = _build_illumio_workload_group_payload("WG-Test", [], {})
        assert payload["object_type"] == "workload_group"

    def test_labels_format(self):
        payload = _build_illumio_workload_group_payload("WG-Test", [], {"app": "eng"})
        assert payload["labels"] == [{"key": "app", "value": "eng"}]

    def test_workloads_have_interfaces(self):
        payload = _build_illumio_workload_group_payload("WG-Test", ["10.1.1.1"], {})
        wl = payload["unmanaged_workloads"][0]
        assert wl["name"] == "10.1.1.1"
        assert wl["interfaces"][0]["address"] == "10.1.1.1"
        assert wl["interfaces"][0]["name"] == "eth0"

    def test_all_ips_included(self):
        ips = ["10.1.1.1", "10.1.1.2", "10.1.1.3"]
        payload = _build_illumio_workload_group_payload("WG-Test", ips, {})
        wl_ips = {wl["interfaces"][0]["address"] for wl in payload["unmanaged_workloads"]}
        assert wl_ips == set(ips)

    def test_empty_ips(self):
        payload = _build_illumio_workload_group_payload("WG-Empty", [], {})
        assert payload["unmanaged_workloads"] == []


class TestBuildIpListPayload:
    def test_required_keys(self):
        payload = _build_illumio_ip_list_payload("IPL-gh", "GitHub", "github.com", ["140.82.121.4"])
        for key in ("object_type", "name", "description", "ip_ranges", "fqdns"):
            assert key in payload

    def test_object_type(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", [])
        assert payload["object_type"] == "ip_list"

    def test_ip_ranges_from_ip_key(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", ["1.2.3.4"])
        assert payload["ip_ranges"][0]["from_ip"] == "1.2.3.4"

    def test_fqdn_fallback_when_no_ips(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", [])
        assert payload["fqdns"] == [{"fqdn": "example.com"}]

    def test_caps_at_50_ips(self):
        ips = [f"1.2.3.{i}" for i in range(100)]
        payload = _build_illumio_ip_list_payload("IPL-big", "Big", "example.com", ips)
        assert len(payload["ip_ranges"]) == 50


class TestBuildServicePayload:
    def test_required_keys(self):
        payload = _build_illumio_service_payload("SVC-HTTPS", "HTTPS", [443])
        for key in ("object_type", "name", "description", "service_ports"):
            assert key in payload

    def test_object_type(self):
        payload = _build_illumio_service_payload("SVC-TEST", "Test", [443])
        assert payload["object_type"] == "service"

    def test_service_ports_tcp(self):
        payload = _build_illumio_service_payload("SVC-SMTP", "SMTP", [25, 587, 465])
        for sp in payload["service_ports"]:
            assert sp["proto"] == 6  # TCP

    def test_multiple_ports_count(self):
        payload = _build_illumio_service_payload("SVC-SMTP", "SMTP", [25, 587, 465])
        assert len(payload["service_ports"]) == 3

    def test_empty_ports(self):
        payload = _build_illumio_service_payload("SVC-EMPTY", "Empty", [])
        assert payload["service_ports"] == []


class TestBuildRulesetPayload:
    def test_required_keys(self):
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", [{"key": "env", "value": "prod"}])
        for key in ("object_type", "name", "description", "scopes", "rules"):
            assert key in payload

    def test_object_type(self):
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", [])
        assert payload["object_type"] == "ruleset"

    def test_scopes_wrapped_as_list_of_lists(self):
        scope = [{"key": "env", "value": "prod"}]
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", scope)
        assert isinstance(payload["scopes"], list)
        assert isinstance(payload["scopes"][0], list)
        assert payload["scopes"][0] == scope

    def test_rules_initially_empty(self):
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", [])
        assert payload["rules"] == []
