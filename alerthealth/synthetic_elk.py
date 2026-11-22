"""ELK (log tabanlı) SENTETİK alarm dokümanları üretir.

UYARI: Veri GERÇEK DEĞİLDİR ve alan adları ECS'ye benzeyen VARSAYIMSAL bir şemadır
(rule.name, host.name, log.level, @timestamp, alert.end, alert.acknowledged_at, labels.*).
Gerçek Kibana alerting / ElastAlert / Watcher şemaları farklıdır; `--field-map` ile uyarlanır.

Incident zaman çizelgesi, ana sentetik üreticiyle (aynı seed) aynıdır: aynı incident'lar log
alarmları olarak da görünür. Böylece kaynaklar arası (Zabbix/Prometheus + ELK) korelasyon denenebilir.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from .schema import AlertEvent
from .synthetic import _ack, generate

LEVEL = {"info": "info", "warning": "warning", "high": "error", "critical": "critical"}


def generate_elk(days: int = 30, hosts: int = 24, seed: int = 42, start: datetime | None = None,
                 tz_offset_hours: float = 3.0) -> list[AlertEvent]:
    start = start or datetime(2026, 9, 1, tzinfo=timezone.utc)
    rng = random.Random(seed + 1000)
    host_names = [f"srv-{i:02d}" for i in range(1, hosts + 1)]
    span = days * 24 * 60

    incidents: dict[str, list[datetime]] = {}
    for e in generate(days=days, hosts=hosts, seed=seed, start=start):
        if e.incident_id:
            window = incidents.setdefault(e.incident_id, [e.started_at, e.started_at])
            window[0] = min(window[0], e.started_at)
            window[1] = max(window[1], e.ended_at or e.started_at)

    events: list[AlertEvent] = []
    seq = 0

    def add(rule, entity, severity, begin, minutes, actionable, ack_p, incident=None):
        nonlocal seq
        seq += 1
        end = begin + timedelta(minutes=minutes)
        hour = (begin + timedelta(hours=tz_offset_hours)).hour
        events.append(AlertEvent(
            id=f"elk-{seq:06d}", source="elk", rule=rule, entity=entity, severity=severity,
            started_at=begin, ended_at=end, acked_at=_ack(rng, begin, end, ack_p, not 7 <= hour < 22),
            actionable=actionable, incident_id=incident, labels={"synthetic": "true"},
        ))

    # 1) Gürültülü log kuralları (kısa, sık, çoğu aksiyon gerektirmez)
    for rule, severity, share in [("ErrorLogRate>50/min", "warning", 0.04), ("SlowQuery>2s", "warning", 0.03),
                                  ("AuthFailureBurst", "warning", 0.08)]:
        for host in rng.sample(host_names, k=max(3, hosts // 5)):
            t = rng.uniform(0, 400)
            while t < span:
                duration = rng.uniform(0.5, 3.5)
                add(rule, host, severity, start + timedelta(minutes=t), duration,
                    actionable=rng.random() < share, ack_p=0.07)
                t += duration + rng.expovariate(1 / rng.uniform(90, 300))

    # 2) Bayat/tekrar eden: her gün yeniden bildirilen, uzun süren log alarmı
    for host in rng.sample(host_names, k=4):
        t = rng.uniform(0, 3 * 24 * 60)
        while t < span:
            add("DiskWatermarkLogWarning", host, "warning", start + timedelta(minutes=t),
                rng.uniform(500, 1300), actionable=rng.random() < 0.1, ack_p=0.22)
            t += 24 * 60 + rng.uniform(-20, 20)

    # 3) Seyrek, gerçek aksiyon gerektiren log alarmları
    for rule, severity, per_month, lo, hi in [("OOMKilledLog", "high", 4, 5, 30), ("TLSHandshakeFailures", "high", 2, 20, 120)]:
        for _ in range(max(1, round(per_month * days / 30))):
            add(rule, rng.choice(host_names), severity, start + timedelta(minutes=rng.uniform(0, span)),
                rng.uniform(lo, hi), actionable=True, ack_p=0.95)

    # 4) Aynı incident'lar log tarafında da görünür
    for incident, (begin, end) in sorted(incidents.items()):
        length = max((end - begin).total_seconds() / 60, 10.0)
        for _ in range(rng.randint(3, 12)):
            offset = rng.uniform(0.3, 9.0)
            rule = rng.choice(["UpstreamTimeoutLogs", "ErrorLogRate>50/min", "ConnectionRefusedLogs"])
            add(rule, rng.choice(host_names), rng.choice(["critical", "high"]), begin + timedelta(minutes=offset),
                max(length - offset, 5.0), actionable=True, ack_p=0.65, incident=incident)

    events.sort(key=lambda e: e.started_at)
    return events


def event_to_doc(event: AlertEvent) -> dict:
    """AlertEvent -> ECS benzeri Elasticsearch dokümanı (iç içe alanlar)."""
    def iso(ts):
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = {
        "@timestamp": iso(event.started_at),
        "rule": {"name": event.rule},
        "host": {"name": event.entity},
        "log": {"level": LEVEL.get(event.severity, "warning")},
        "alert": {},
        "labels": {"synthetic": "true", "actionable": event.actionable},
    }
    if event.ended_at:
        doc["alert"]["end"] = iso(event.ended_at)
    if event.acked_at:
        doc["alert"]["acknowledged_at"] = iso(event.acked_at)
    if event.incident_id:
        doc["labels"]["incident"] = event.incident_id
    return doc


# Bu dokümanları adaptörün okuması için alan eşlemesi:
FIELD_MAP = {
    "rule": "rule.name", "entity": "host.name", "severity": "log.level", "started_at": "@timestamp",
    "ended_at": "alert.end", "acked_at": "alert.acknowledged_at",
    "actionable": "labels.actionable", "incident_id": "labels.incident",
}
