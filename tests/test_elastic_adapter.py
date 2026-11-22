"""Elasticsearch adaptörü, yerel sahte bir sunucuya karşı (gerçek küme değil)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from alerthealth.adapters import elastic

PAGES = [
    {"_scroll_id": "s1", "hits": {"hits": [
        {"_id": "a1", "_source": {"rule_name": "HighCPU", "host": {"name": "srv-01"}, "severity": "warning",
                                  "@timestamp": "2026-01-01T10:00:00Z", "recovered_at": "2026-01-01T10:03:00Z"}},
    ]}},
    {"_scroll_id": "s1", "hits": {"hits": [
        {"_id": "a2", "_source": {"rule_name": "ServiceDown", "host": {"name": "srv-02"}, "severity": "disaster",
                                  "@timestamp": "2026-01-01T11:00:00Z"}},
    ]}},
    {"_scroll_id": "s1", "hits": {"hits": []}},
]


def _server():
    queue = list(PAGES)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            body = json.dumps(queue.pop(0)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def test_collect_maps_fields_and_pages():
    httpd = _server()
    try:
        events = elastic.collect(f"http://127.0.0.1:{httpd.server_port}", "alerts-*", hours=24)
    finally:
        httpd.shutdown()
    assert [e.rule for e in events] == ["HighCPU", "ServiceDown"]
    assert events[0].entity == "srv-01" and events[0].ended_at is not None
    assert events[1].severity == "critical" and events[1].ended_at is None


def test_custom_field_map():
    hit = {"_id": "x", "_source": {"r": "R", "t": "2026-01-01T00:00:00Z", "h": "H"}}
    event = elastic.hit_to_event(hit, {**elastic.DEFAULT_FIELD_MAP, "rule": "r", "started_at": "t", "entity": "h"})
    assert event.rule == "R" and event.entity == "H"


def test_dig_supports_flat_dotted_and_nested_keys():
    assert elastic._dig({"host.name": "a"}, "host.name") == "a"
    assert elastic._dig({"host": {"name": "b"}}, "host.name") == "b"
    assert elastic._dig({"kibana.alert": {"rule.name": "c"}}, "kibana.alert.rule.name") == "c"
    assert elastic._dig({"x": 1}, "host.name") is None


def test_optional_label_fields():
    hit = {"_id": "1", "_source": {"rule_name": "R", "@timestamp": "2026-01-01T00:00:00Z",
                                   "labels": {"actionable": False, "incident": "INC-9"}}}
    mapping = {**elastic.DEFAULT_FIELD_MAP, "actionable": "labels.actionable", "incident_id": "labels.incident"}
    event = elastic.hit_to_event(hit, mapping)
    assert event.actionable is False and event.incident_id == "INC-9"
