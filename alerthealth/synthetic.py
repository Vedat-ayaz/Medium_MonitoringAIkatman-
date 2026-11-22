"""Sentetik alert geçmişi üreticisi.

UYARI: Bu veri GERÇEK DEĞİLDİR. Bilinen davranışlara sahip (gürültülü, tekrar eden, incident
dalgası yaratan) kurallardan oluşan, tekrarlanabilir bir test verisidir. Aracı doğrulamak ve
yazıda yöntemi göstermek içindir; sonuçlar bir ortam kıyaslaması değildir.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from .schema import AlertEvent

# (kural, önem, davranış)
FLAPPERS = [("HighCPU>80%", "warning"), ("PingLoss", "warning"), ("HighLoadAverage", "warning")]


def _ack(rng: random.Random, start: datetime, end: datetime | None, p: float, night: bool) -> datetime | None:
    if rng.random() > p:
        return None
    median = 14.0 if night else 6.0
    # Onay, alarm kapandıktan sonra da gelebilir (biri sonradan "gördüm" der); süreye göre kırpılmaz.
    delay = min(rng.lognormvariate(0.0, 0.7) * median, 240.0)
    return start + timedelta(minutes=delay)


def generate(days: int = 30, hosts: int = 24, seed: int = 42, start: datetime | None = None,
             tz_offset_hours: float = 3.0) -> list[AlertEvent]:
    rng = random.Random(seed)
    start = start or datetime(2026, 9, 1, tzinfo=timezone.utc)
    host_names = [f"srv-{i:02d}" for i in range(1, hosts + 1)]
    events: list[AlertEvent] = []
    seq = 0

    def add(rule: str, entity: str, severity: str, begin: datetime, minutes: float, actionable: bool,
            ack_p: float, incident: str | None = None, open_ended: bool = False) -> None:
        nonlocal seq
        seq += 1
        end = None if open_ended else begin + timedelta(minutes=minutes)
        hour = (begin + timedelta(hours=tz_offset_hours)).hour
        events.append(AlertEvent(
            id=f"syn-{seq:06d}", source="synthetic", rule=rule, entity=entity, severity=severity,
            started_at=begin, ended_at=end, acked_at=_ack(rng, begin, end, ack_p, not 7 <= hour < 22),
            actionable=actionable, incident_id=incident, labels={"synthetic": "true"},
        ))

    span_minutes = days * 24 * 60

    # 1) Gürültülü, tekrar eden (flapping) kurallar: kısa süreli, çoğu aksiyon gerektirmez
    for rule, severity in FLAPPERS:
        for host in rng.sample(host_names, k=max(3, hosts // 4)):
            t = rng.uniform(0, 600)
            while t < span_minutes:
                duration = rng.uniform(0.5, 4.0)
                add(rule, host, severity, start + timedelta(minutes=t), duration,
                    actionable=rng.random() < 0.03, ack_p=0.08)
                t += duration + rng.expovariate(1 / rng.uniform(60, 240))  # saatler arası, kümeli

    # 2) Disk uyarısı: uzun süren, her gün yeniden bildirilen (tekrar eden) alarm
    for host in rng.sample(host_names, k=6):
        t = rng.uniform(0, 5 * 24 * 60)
        while t < span_minutes:
            add("DiskUsage>80%", host, "warning", start + timedelta(minutes=t), rng.uniform(600, 1400),
                actionable=rng.random() < 0.12, ack_p=0.25)
            t += 24 * 60 + rng.uniform(-30, 30)

    # 3) Seyrek ve gerçekten aksiyon gerektiren kurallar
    for rule, severity, per_month, lo, hi in [
        ("ServiceDown", "high", 5, 5, 40), ("BackupJobFailed", "high", 4, 60, 300),
        ("DBReplicationLag", "high", 3, 10, 90), ("CertExpiry<30d", "info", 3, 1440, 4320),
    ]:
        for _ in range(max(1, round(per_month * days / 30))):
            add(rule, rng.choice(host_names), severity,
                start + timedelta(minutes=rng.uniform(0, span_minutes)), rng.uniform(lo, hi),
                actionable=True, ack_p=0.95)

    # 4) Incident'lar: bir kök neden, kısa sürede onlarca bağımlı alarm
    for n in range(1, max(2, round(12 * days / 30)) + 1):
        incident = f"INC-{n:03d}"
        begin = start + timedelta(minutes=rng.uniform(0, span_minutes - 240))
        length = rng.uniform(15, 120)
        root_host = rng.choice(host_names)
        add(rng.choice(["DBReplicationLag", "ServiceDown"]), root_host, "high", begin, length,
            actionable=True, ack_p=1.0, incident=incident)
        for _ in range(rng.randint(5, 25)):
            offset = rng.uniform(0.2, 8.0)
            rule = rng.choice(["HTTP5xxRate>5%", "LatencyP95>1s", "QueueBacklog", "HealthcheckFailed"])
            add(rule, rng.choice(host_names), rng.choice(["critical", "high"]),
                begin + timedelta(minutes=offset), max(length - offset, 5.0),
                actionable=True, ack_p=0.7, incident=incident)

    # 5) Birkaç alarm hâlâ açık
    for _ in range(3):
        add("DiskUsage>90%", rng.choice(host_names), "high",
            start + timedelta(minutes=span_minutes - rng.uniform(30, 600)), 0, True, 0.6, open_ended=True)

    events.sort(key=lambda e: e.started_at)
    return events
