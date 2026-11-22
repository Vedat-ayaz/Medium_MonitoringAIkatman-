"""Elasticsearch API'siyle UYUMLU SAHTE sunucu (stand-in). GERÇEK ELASTICSEARCH DEĞİLDİR.

Gerçek Elasticsearch/Kibana, test ortamında kurulamadığı için, alerthealth'in Elasticsearch
adaptörünü HTTP üzerinden uçtan uca denemek için yazıldı. Desteklenen minimum yüzey:
  GET  /                              küme bilgisi (stand-in olduğunu söyler)
  POST /<index>/_search?scroll=2m     match_all ve range (gte/lte: ISO veya now-<n>h|m|d); index'te '*' desteklenir
  POST /_search/scroll                sayfalama
  PUT|POST /<index>/_doc/<id>         doküman ekleme
  POST /_bulk                         NDJSON ekleme (index/create)
  GET  /<index>/_count
Desteklenmeyenler: aggregation, sort, mapping, analiz, kimlik doğrulama (gelen başlıklar yok sayılır).
Kullanım: python3 lab/elk/stub_es.py --port 9200 --load alerts-synthetic=data/synthetic/elk_alerts_30d.ndjson \
          [--now 2026-10-02T00:00:00Z]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from alerthealth.adapters.elastic import _dig  # noqa: E402
from alerthealth.schema import parse_ts  # noqa: E402

INDICES: dict[str, list[tuple[str, dict]]] = {}
SCROLLS: dict[str, dict] = {}
NOW_OVERRIDE: datetime | None = None
_DURATION = re.compile(r"^now-(\d+)([mhd])$")


def _now() -> datetime:
    return NOW_OVERRIDE or datetime.now(timezone.utc)


def _bound(value) -> datetime:
    match = _DURATION.match(str(value))
    if match:
        n, unit = int(match.group(1)), match.group(2)
        return _now() - timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: n})
    if str(value) == "now":
        return _now()
    return parse_ts(value)


def _matches(source: dict, query: dict) -> bool:
    if not query or "match_all" in query:
        return True
    if "range" in query:
        for field, bounds in query["range"].items():
            raw = _dig(source, field)
            ts = parse_ts(raw) if raw is not None else None
            if ts is None:
                return False
            if "gte" in bounds and ts < _bound(bounds["gte"]):
                return False
            if "gt" in bounds and ts <= _bound(bounds["gt"]):
                return False
            if "lte" in bounds and ts > _bound(bounds["lte"]):
                return False
            if "lt" in bounds and ts >= _bound(bounds["lt"]):
                return False
        return True
    raise ValueError(f"desteklenmeyen sorgu: {list(query)}")


def _page(scroll_id: str) -> dict:
    state = SCROLLS[scroll_id]
    chunk = state["hits"][state["pos"]:state["pos"] + state["size"]]
    state["pos"] += state["size"]
    return {"_scroll_id": scroll_id, "took": 1, "timed_out": False,
            "hits": {"total": {"value": len(state["hits"]), "relation": "eq"}, "hits": chunk}}


def search(index_expr: str, body: dict) -> dict:
    hits = []
    for name, docs in INDICES.items():
        if any(fnmatch.fnmatch(name, pattern) for pattern in index_expr.split(",")):
            hits += [{"_index": name, "_id": doc_id, "_source": src} for doc_id, src in docs
                     if _matches(src, body.get("query", {}))]
    hits.sort(key=lambda h: str(_dig(h["_source"], "@timestamp")))
    scroll_id = uuid.uuid4().hex
    SCROLLS[scroll_id] = {"hits": hits, "pos": 0, "size": int(body.get("size", 10))}
    return _page(scroll_id)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Stub", "true")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, {"name": "stub-es", "cluster_name": "es-compatible-stub",
                                    "version": {"number": "0.0-stub"},
                                    "tagline": "NOT Elasticsearch: test stand-in for alerthealth"})
        match = re.fullmatch(r"/([^/]+)/_count", path)
        if match:
            total = sum(len(d) for n, d in INDICES.items() if fnmatch.fnmatch(n, match.group(1)))
            return self._send(200, {"count": total})
        self._send(404, {"error": "stub: desteklenmeyen yol", "path": path})

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path, raw = parsed.path, self._body()
        try:
            if path == "/_search/scroll":
                body = json.loads(raw or b"{}")
                scroll_id = body.get("scroll_id")
                if scroll_id not in SCROLLS:
                    return self._send(404, {"error": "unknown scroll_id"})
                return self._send(200, _page(scroll_id))
            if path == "/_bulk":
                lines = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
                items, i = [], 0
                while i < len(lines):
                    action = lines[i]
                    meta = next(iter(action.values()))
                    INDICES.setdefault(meta["_index"], []).append((meta.get("_id") or uuid.uuid4().hex, lines[i + 1]))
                    items.append({"index": {"status": 201}})
                    i += 2
                return self._send(200, {"errors": False, "items": items})
            match = re.fullmatch(r"/([^/]+)/_search", path)
            if match:
                return self._send(200, search(match.group(1), json.loads(raw or b"{}")))
            match = re.fullmatch(r"/([^/]+)/_doc(?:/([^/]+))?", path)
            if match:
                INDICES.setdefault(match.group(1), []).append((match.group(2) or uuid.uuid4().hex, json.loads(raw)))
                return self._send(201, {"result": "created"})
        except (ValueError, KeyError) as exc:
            return self._send(400, {"error": str(exc)})
        self._send(404, {"error": "stub: desteklenmeyen yol", "path": path})

    do_PUT = do_POST  # noqa: N815

    def log_message(self, *_args):
        pass


def load_ndjson(index: str, path: str) -> int:
    docs = INDICES.setdefault(index, [])
    with open(path, encoding="utf-8") as handle:
        for n, line in enumerate(handle, 1):
            if line.strip():
                docs.append((f"{index}-{n:06d}", json.loads(line)))
    return len(docs)


def main() -> int:
    global NOW_OVERRIDE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9200)
    ap.add_argument("--load", action="append", default=[], help="index=dosya.ndjson (tekrarlanabilir)")
    ap.add_argument("--now", help="'now-Nh' sorguları için sabit zaman (ISO), sentetik eski veri içindir")
    args = ap.parse_args()
    if args.now:
        NOW_OVERRIDE = parse_ts(args.now)
    for spec in args.load:
        index, _, path = spec.partition("=")
        print(f"yüklendi: {index} ({load_ndjson(index, path)} doküman)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
