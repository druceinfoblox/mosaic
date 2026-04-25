"""Tests for Illumio dry-run payload generation.

These tests validate that the builder functions produce payloads that are
structurally compatible with the Illumio PCE REST API, without requiring
a live PCE connection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.recommender import (
    _build_illumio_workload_group_payload,
    _build_illumio_ip_list_payload,
    _build_illumio_service_payload,
    _build_illumio_ruleset_payload,
    _infer_ports_from_fqdn,
)


DEMO_IPS = ["10.1.1.1", "10.1.1.2", "10.1.1.3"]
DEMO_LABELS = {"app": "finance", "env": "discovered"}
PUBLIC_IPS = ["140.82.121.4", "192.30.255.112", "185.199.108.133"]


class TestWorkloadGroupDryRun:
    """WORKLOAD_GROUP dry-run payloads."""

    def test_all_api_fields_present(self):
        payload = _build_illumio_workload_group_payload("WG-Finance", DEMO_IPS, DEMO_LABELS)
        for field in ("object_type", "name", "description", "labels", "unmanaged_workloads"):
            assert field in payload, f"Missing required Illumio API field: {field}"

    def test_name_preserved_verbatim(self):
        payload = _build_illumio_workload_group_payload("WG-Finance-10_1_1", DEMO_IPS, DEMO_LABELS)
        assert payload["name"] == "WG-Finance-10_1_1"

    def test_label_key_value_pairs(self):
        payload = _build_illumio_workload_group_payload("WG-Test", DEMO_IPS, DEMO_LABELS)
        label_map = {lbl["key"]: lbl["value"] for lbl in payload["labels"]}
        assert label_map["app"] == "finance"
        assert label_map["env"] == "discovered"

    def test_each_workload_has_eth0_interface(self):
        payload = _build_illumio_workload_group_payload("WG-Test", DEMO_IPS, DEMO_LABELS)
        for wl in payload["unmanaged_workloads"]:
            iface = wl["interfaces"][0]
            assert iface["name"] == "eth0"
            assert iface["address"] in DEMO_IPS

    def test_ip_count_matches(self):
        payload = _build_illumio_workload_group_payload("WG-Test", DEMO_IPS, DEMO_LABELS)
        assert len(payload["unmanaged_workloads"]) == len(DEMO_IPS)

    def test_empty_labels_still_valid(self):
        payload = _build_illumio_workload_group_payload("WG-Test", DEMO_IPS, {})
        assert payload["labels"] == []

    def test_no_ips_produces_empty_workloads(self):
        payload = _build_illumio_workload_group_payload("WG-Empty", [], {})
        assert payload["unmanaged_workloads"] == []

    def test_description_is_string(self):
        payload = _build_illumio_workload_group_payload("WG-Test", DEMO_IPS, DEMO_LABELS)
        assert isinstance(payload["description"], str) and len(payload["description"]) > 0


class TestIpListDryRun:
    """IP_LIST dry-run payloads."""

    def test_all_api_fields_present(self):
        payload = _build_illumio_ip_list_payload("IPL-github", "GitHub", "github.com", PUBLIC_IPS)
        for field in ("object_type", "name", "description", "ip_ranges", "fqdns"):
            assert field in payload, f"Missing required Illumio API field: {field}"

    def test_ip_ranges_use_from_ip_key(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", PUBLIC_IPS)
        for rng in payload["ip_ranges"]:
            assert "from_ip" in rng

    def test_all_public_ips_in_ranges(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", PUBLIC_IPS)
        ip_set = {r["from_ip"] for r in payload["ip_ranges"]}
        assert ip_set == set(PUBLIC_IPS)

    def test_fqdn_list_has_fqdn_key(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", [])
        for entry in payload["fqdns"]:
            assert "fqdn" in entry

    def test_fqdn_fallback_when_no_answer_ips(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", [])
        assert len(payload["fqdns"]) > 0
        assert payload["fqdns"][0]["fqdn"] == "example.com"

    def test_50_ip_cap_enforced(self):
        many_ips = [f"1.2.{i // 256}.{i % 256}" for i in range(200)]
        payload = _build_illumio_ip_list_payload("IPL-big", "Big", "big.com", many_ips)
        assert len(payload["ip_ranges"]) <= 50

    def test_object_type_is_ip_list(self):
        payload = _build_illumio_ip_list_payload("IPL-test", "Test", "example.com", [])
        assert payload["object_type"] == "ip_list"


class TestServiceDryRun:
    """SERVICE dry-run payloads."""

    def test_all_api_fields_present(self):
        payload = _build_illumio_service_payload("SVC-HTTPS-443", "HTTPS", [443])
        for field in ("object_type", "name", "description", "service_ports"):
            assert field in payload, f"Missing required Illumio API field: {field}"

    def test_service_ports_use_tcp_proto_6(self):
        payload = _build_illumio_service_payload("SVC-SMTP", "SMTP", [25, 587, 465])
        for sp in payload["service_ports"]:
            assert sp["proto"] == 6, "Illumio requires proto=6 for TCP"

    def test_port_numbers_preserved(self):
        payload = _build_illumio_service_payload("SVC-DB", "DB", [5432, 1433, 3306])
        ports = {sp["port"] for sp in payload["service_ports"]}
        assert ports == {5432, 1433, 3306}

    def test_smtp_port_inference(self):
        ports = _infer_ports_from_fqdn("smtp.relay.corp.com")
        assert 25 in ports and 587 in ports

    def test_ldap_port_inference(self):
        ports = _infer_ports_from_fqdn("ldap.corp.local")
        assert 389 in ports

    def test_empty_ports_list(self):
        payload = _build_illumio_service_payload("SVC-EMPTY", "Empty", [])
        assert payload["service_ports"] == []

    def test_object_type_is_service(self):
        payload = _build_illumio_service_payload("SVC-TEST", "Test", [443])
        assert payload["object_type"] == "service"


class TestRulesetDryRun:
    """APP_DEPENDENCY ruleset dry-run payloads."""

    def test_all_api_fields_present(self):
        payload = _build_illumio_ruleset_payload(
            "DEP-github", "Auto-generated for github.com",
            [{"key": "env", "value": "discovered"}],
        )
        for field in ("object_type", "name", "description", "scopes", "rules"):
            assert field in payload, f"Missing required Illumio API field: {field}"

    def test_scopes_is_list_of_scope_arrays(self):
        scope = [{"key": "env", "value": "discovered"}]
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", scope)
        assert isinstance(payload["scopes"], list)
        assert isinstance(payload["scopes"][0], list)

    def test_scope_labels_have_key_value(self):
        scope = [{"key": "env", "value": "prod"}, {"key": "app", "value": "web"}]
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", scope)
        for label in payload["scopes"][0]:
            assert "key" in label and "value" in label

    def test_rules_start_empty(self):
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", [])
        assert payload["rules"] == []
        assert isinstance(payload["rules"], list)

    def test_object_type_is_ruleset(self):
        payload = _build_illumio_ruleset_payload("RS-Test", "Test", [])
        assert payload["object_type"] == "ruleset"

    def test_empty_scope_creates_valid_structure(self):
        payload = _build_illumio_ruleset_payload("RS-Empty", "Empty scope", [])
        assert payload["scopes"] == [[]]
