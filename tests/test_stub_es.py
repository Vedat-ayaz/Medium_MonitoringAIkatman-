"""ES-uyumlu stand-in sunucu + adaptör uçtan uca (HTTP üzerinden). Gerçek Elasticsearch değildir."""
import importlib.util
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from alerthealth.adapters import elastic
from alerthealth.schema import parse_ts

_spec = importlib.util.spec_from_file_location("stub_es", Path(__file__).resolve().parents[1] / "lab/elk/stub_es.py")
stub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stub)


def _docs(n):
    return [{"@timestamp": f"2026-01-01T00:{i:02d}:00Z", "rule": {"name": f"R{i % 3}"}, "host": {"name": "h"},
             "log": {"level": "error"}, "alert": {"end": f"2026-01-01T00:{i:02d}:30Z"}} for i in range(n)]


def test_paging_range_filter_and_mapping_end_to_end():
    stub.INDICES.clear()
    stub.INDICES["alerts-test"] = [(f"id{i}", d) for i, d in enumerate(_docs(25))]
    stub.NOW_OVERRIDE = parse_ts("2026-01-01T01:00:00Z")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), stub.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    mapping = {"rule": "rule.name", "entity": "host.name", "severity": "log.level",
               "started_at": "@timestamp", "ended_at": "alert.end"}
    try:
        url = f"http://127.0.0.1:{httpd.server_port}"
        # sayfa boyutu (1000) < 25 değil; scroll sonunu da denemek için küçük sayfa:
        hits = list(elastic.scan(url, "alerts-*", {"match_all": {}}, {"Content-Type": "application/json"}, page_size=7))
        everything = elastic.collect(url, "alerts-*", field_map=mapping, hours=1)
        recent = elastic.collect(url, "alerts-*", field_map=mapping, hours=0.2)  # son 12 dk: 00:48-01:00 -> yok
        window = elastic.collect(url, "alerts-*", field_map=mapping, hours=0.6)  # son 36 dk: 00:24'ten itibaren
    finally:
        httpd.shutdown()
        stub.NOW_OVERRIDE = None
    assert len(hits) == 25                      # 7+7+7+4 sayfa, hiçbiri kaybolmadı
    assert len(everything) == 25 and everything[0].severity == "high"
    assert recent == []                         # range filtresi çalışıyor
    assert len(window) == 1                     # 1 saatten kısa pencere (0,6 sa = 36 dk) doğru kesiliyor
