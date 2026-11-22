"""Elasticsearch adaptörü: alert kayıtlarının tutulduğu bir indeksten olay çıkarır.

Alanlar ortamdan ortama değişir (ElastAlert, Kibana alerting, Watcher geçmişi, kendi indeksin...).
Bu yüzden alan eşlemesi (field_map) kullanıcıdan alınır; noktalı yol desteklenir (ör. "host.name").
İsteğe bağlı eşlemeler: "actionable" (insan etiketi) ve "incident_id".
NOT: Bu adaptör şu ana kadar yalnızca Elasticsearch API'siyle uyumlu SAHTE sunuculara karşı test edildi
(tests/ ve lab/elk/stub_es.py). Gerçek bir Elasticsearch kümesine karşı doğrulanmadı.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Iterator, Optional

from ..schema import AlertEvent, normalize_severity, parse_ts

DEFAULT_FIELD_MAP = {
    "id": "_id", "rule": "rule_name", "entity": "host.name", "severity": "severity",
    "started_at": "@timestamp", "ended_at": "recovered_at", "acked_at": "acknowledged_at",
}


def _dig(doc: dict, path: str):
    """Noktalı yolu çözer. Elasticsearch iki biçimi de saklar: iç içe ({"host": {"name": ..}})
    ve düz noktalı anahtar ({"host.name": ..}); ikisi de desteklenir."""
    if path in doc:
        return doc[path]
    parts = path.split(".")
    for i in range(1, len(parts)):  # "a.b" + "c" gibi karışık biçimler
        head = ".".join(parts[:i])
        if head in doc and isinstance(doc[head], dict):
            return _dig(doc[head], ".".join(parts[i:]))
    return None


def _post(url: str, body: dict, headers: dict, timeout: float = 60.0) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def scan(url: str, index: str, query: dict, headers: dict, page_size: int = 1000) -> Iterator[dict]:
    base = url.rstrip("/")
    page = _post(f"{base}/{index}/_search?scroll=2m", {"size": page_size, "query": query}, headers)
    scroll_id = page.get("_scroll_id")
    while page["hits"]["hits"]:
        yield from page["hits"]["hits"]
        if not scroll_id:
            break
        page = _post(f"{base}/_search/scroll", {"scroll": "2m", "scroll_id": scroll_id}, headers)
        scroll_id = page.get("_scroll_id", scroll_id)


def hit_to_event(hit: dict, field_map: dict) -> Optional[AlertEvent]:
    doc = dict(hit.get("_source", {}))
    doc["_id"] = hit.get("_id")

    def pick(name: str):
        path = field_map.get(name)
        return _dig(doc, path) if path else None

    started = parse_ts(pick("started_at"))
    rule = pick("rule")
    if started is None or rule is None:
        return None
    return AlertEvent(
        id=f"elk:{pick('id')}", source="elk", rule=str(rule), entity=str(pick("entity") or "unknown"),
        severity=normalize_severity(pick("severity")), started_at=started,
        ended_at=parse_ts(pick("ended_at")), acked_at=parse_ts(pick("acked_at")),
        actionable=pick("actionable"), incident_id=pick("incident_id"),
    )


def collect(url: str, index: str, field_map: Optional[dict] = None, hours: float = 24.0,
            api_key: Optional[str] = None, extra_headers: Optional[dict] = None) -> list[AlertEvent]:
    mapping = {**DEFAULT_FIELD_MAP, **(field_map or {})}
    headers = {"Content-Type": "application/json", **(extra_headers or {})}
    if api_key:
        headers["Authorization"] = f"ApiKey {api_key}"
    query = {"range": {mapping["started_at"]: {"gte": f"now-{max(1, round(hours * 60))}m"}}}
    events = [e for e in (hit_to_event(h, mapping) for h in scan(url, index, query, headers)) if e]
    return sorted(events, key=lambda e: e.started_at)
