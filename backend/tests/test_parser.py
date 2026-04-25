"""Tests for DNS log parser — CSV, JSON, and syslog formats."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.parser import (
    parse_dns_logs,
    parse_csv,
    parse_json,
    parse_syslog,
    _detect_format,
    _parse_answer_ips,
    _parse_timestamp,
)


CSV_SAMPLE = """timestamp,client_ip,fqdn,qtype,rcode,answer_ips
2026-04-01T10:00:00,10.1.1.10,github.com,A,NOERROR,140.82.121.4
2026-04-01T10:01:00,10.1.1.11,salesforce.com,A,NOERROR,204.14.232.100
2026-04-01T10:02:00,10.1.2.10,ad.corp.local,A,NOERROR,10.1.4.10,10.1.4.11
"""

JSON_ARRAY_SAMPLE = """[
  {"timestamp": "2026-04-01T10:00:00", "client_ip": "10.1.1.10", "fqdn": "github.com", "qtype": "A", "rcode": "NOERROR", "answer_ips": "140.82.121.4"},
  {"timestamp": "2026-04-01T10:01:00", "client_ip": "10.1.1.11", "fqdn": "salesforce.com", "qtype": "A", "rcode": "NOERROR", "answer_ips": ["204.14.232.100"]}
]"""

JSON_WRAPPED_SAMPLE = """{"records": [
  {"timestamp": "2026-04-01T10:00:00", "client_ip": "10.1.1.10", "fqdn": "github.com", "qtype": "A", "rcode": "NOERROR"}
]}"""

SYSLOG_SAMPLE = (
    "Apr  1 10:00:00 ns1 named[1234]: client 10.1.1.10#12345: query: github.com IN A +E (8.8.8.8)\n"
    "Apr  1 10:01:00 ns1 named[1234]: client 10.1.1.11#54321: query: salesforce.com IN A +E (8.8.8.8)"
)


class TestDetectFormat:
    def test_csv(self):
        assert _detect_format(CSV_SAMPLE) == "csv"

    def test_json_array(self):
        assert _detect_format(JSON_ARRAY_SAMPLE) == "json"

    def test_json_object(self):
        assert _detect_format(JSON_WRAPPED_SAMPLE) == "json"

    def test_syslog(self):
        assert _detect_format(SYSLOG_SAMPLE) == "syslog"

    def test_csv_without_headers_falls_back_on_commas(self):
        csv_no_header = "2026-04-01,10.1.1.1,github.com,A,NOERROR"
        result = _detect_format(csv_no_header)
        assert result in ("csv", "syslog")


class TestParseTimestamp:
    def test_iso_with_z(self):
        ts = _parse_timestamp("2026-04-01T10:00:00Z")
        assert ts.year == 2026 and ts.month == 4 and ts.day == 1

    def test_iso_with_milliseconds(self):
        ts = _parse_timestamp("2026-04-01T10:00:00.123Z")
        assert ts.year == 2026

    def test_iso_no_z(self):
        ts = _parse_timestamp("2026-04-01T10:00:00")
        assert ts.year == 2026

    def test_date_space_time(self):
        ts = _parse_timestamp("2026-04-01 10:00:00")
        assert ts.year == 2026

    def test_invalid_returns_utcnow(self):
        from datetime import datetime
        ts = _parse_timestamp("not-a-date")
        assert isinstance(ts, datetime)


class TestParseAnswerIps:
    def test_comma_separated(self):
        assert _parse_answer_ips("10.1.1.1,10.1.1.2") == ["10.1.1.1", "10.1.1.2"]

    def test_semicolon_separated(self):
        assert _parse_answer_ips("10.1.1.1;10.1.1.2") == ["10.1.1.1", "10.1.1.2"]

    def test_empty_string(self):
        assert _parse_answer_ips("") == []

    def test_list_passthrough(self):
        result = _parse_answer_ips(["10.1.1.1", "10.1.1.2"])  # type: ignore[arg-type]
        assert result == ["10.1.1.1", "10.1.1.2"]

    def test_filters_non_ips(self):
        result = _parse_answer_ips("10.1.1.1,notanip,10.1.1.2")
        assert "notanip" not in result
        assert "10.1.1.1" in result and "10.1.1.2" in result


class TestParseCsv:
    def test_parses_all_rows(self):
        events = parse_csv(CSV_SAMPLE)
        assert len(events) == 3

    def test_client_ip(self):
        events = parse_csv(CSV_SAMPLE)
        assert events[0].client_ip == "10.1.1.10"

    def test_fqdn_set(self):
        events = parse_csv(CSV_SAMPLE)
        assert events[0].fqdn == "github.com"

    def test_answer_ips_parsed(self):
        events = parse_csv(CSV_SAMPLE)
        assert "10.1.4.10" in events[2].answer_ips

    def test_rcode_uppercase(self):
        events = parse_csv(CSV_SAMPLE)
        assert events[0].rcode == "NOERROR"

    def test_skips_empty_rows(self):
        bad = "timestamp,client_ip,fqdn\n,,"
        assert parse_csv(bad) == []

    def test_trailing_dot_stripped_from_fqdn(self):
        csv = "timestamp,client_ip,fqdn\n2026-04-01T10:00:00,10.1.1.1,github.com."
        events = parse_csv(csv)
        assert events[0].fqdn == "github.com"


class TestParseJson:
    def test_parses_array(self):
        events = parse_json(JSON_ARRAY_SAMPLE)
        assert len(events) == 2

    def test_parses_wrapped_records(self):
        events = parse_json(JSON_WRAPPED_SAMPLE)
        assert len(events) == 1

    def test_client_ip(self):
        events = parse_json(JSON_ARRAY_SAMPLE)
        assert events[0].client_ip == "10.1.1.10"

    def test_invalid_json_returns_empty(self):
        assert parse_json("not json") == []

    def test_fqdn_trailing_dot_stripped(self):
        sample = '[{"timestamp": "2026-04-01T10:00:00", "client_ip": "10.1.1.1", "fqdn": "example.com."}]'
        events = parse_json(sample)
        assert events[0].fqdn == "example.com"


class TestParseSyslog:
    def test_parses_lines(self):
        events = parse_syslog(SYSLOG_SAMPLE)
        assert len(events) == 2

    def test_client_ip(self):
        events = parse_syslog(SYSLOG_SAMPLE)
        assert events[0].client_ip == "10.1.1.10"

    def test_fqdn(self):
        events = parse_syslog(SYSLOG_SAMPLE)
        assert events[0].fqdn == "github.com"

    def test_empty_content(self):
        assert parse_syslog("") == []


class TestParseDnsLogs:
    def test_auto_detects_csv(self):
        assert len(parse_dns_logs(CSV_SAMPLE)) == 3

    def test_auto_detects_json(self):
        assert len(parse_dns_logs(JSON_ARRAY_SAMPLE)) == 2

    def test_auto_detects_syslog(self):
        assert len(parse_dns_logs(SYSLOG_SAMPLE)) >= 1

    def test_empty_returns_empty(self):
        assert parse_dns_logs("") == []
