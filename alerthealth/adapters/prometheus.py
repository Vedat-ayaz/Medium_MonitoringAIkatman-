"""Prometheus adaptörü: ALERTS zaman serisinden alert olayı (başlangıç/bitiş) çıkarır."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from ..schema import AlertEvent, normalize_severity


def _get(url: str, params: dict, timeout: float = 30.0) -> dict:
    full = f"{url.rstrip('/')}/api/v1/query_range?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=timeout) as resp:  # noqa: S310 (kullanıcı verdiği URL)
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus hatası: {payload}")
    return payload["data"]


def series_to_events(series: list[dict], step: float, now: float, source: str = "prometheus") -> list[AlertEvent]:
    """Ardışık örnekleri (boşluk <= 2*step) tek alert aralığına birleştirir."""
    events: list[AlertEvent] = []
    for item in series:
        labels = item["metric"]
        values = sorted(float(ts) for ts, _ in item["values"])
        if not values:
            continue
        begin = prev = values[0]
        intervals = []
        for ts in values[1:]:
            if ts - prev > 2 * step:
                intervals.append((begin, prev))
                begin = ts
            prev = ts
        intervals.append((begin, prev))

        rule = labels.get("alertname", "unknown")
        entity = labels.get("instance") or labels.get("job") or "unknown"
        for start_ts, last_ts in intervals:
            still_open = now - last_ts <= 2 * step
            end_ts = None if still_open else last_ts + step
            events.append(AlertEvent(
                id=f"prom:{rule}:{entity}:{int(start_ts)}", source=source, rule=rule, entity=entity,
                severity=normalize_severity(labels.get("severity")),
                started_at=datetime.fromtimestamp(start_ts, tz=timezone.utc),
                ended_at=datetime.fromtimestamp(end_ts, tz=timezone.utc) if end_ts else None,
                labels={k: v for k, v in labels.items() if k not in ("__name__", "alertstate")},
            ))
    return sorted(events, key=lambda e: e.started_at)


def collect(url: str, hours: float = 24.0, step: float = 15.0) -> list[AlertEvent]:
    end = time.time()
    data = _get(url, {"query": 'ALERTS{alertstate="firing"}', "start": end - hours * 3600, "end": end, "step": step})
    return series_to_events(data["result"], step=step, now=end)
