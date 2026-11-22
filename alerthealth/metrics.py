"""Alert sağlık metrikleri: hacim, gürültü, tekrar, MTTA/MTTR, gece sayfalama, burst'ler."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import timedelta
from typing import Optional, Sequence

from .schema import AlertEvent

MIN_RULE_COUNT = 10  # bunun altındaki kurallar için "gürültülü" yargısı verilmez


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    if not values:
        return None
    data = sorted(values)
    if len(data) == 1:
        return float(data[0])
    k = (len(data) - 1) * p
    low, high = int(k), min(int(k) + 1, len(data) - 1)
    return float(data[low] + (data[high] - data[low]) * (k - low))


def _minutes(delta: timedelta) -> float:
    return delta.total_seconds() / 60.0


def _rule_stats(events: list[AlertEvent], days: float, short_min: float, flap_gap_min: float) -> list[dict]:
    by_rule: dict[str, list[AlertEvent]] = defaultdict(list)
    for event in events:
        by_rule[event.rule].append(event)

    rows = []
    for rule, items in by_rule.items():
        durations = [_minutes(e.ended_at - e.started_at) for e in items if e.ended_at]
        short_share = (sum(1 for d in durations if d < short_min) / len(durations)) if durations else None

        flaps = 0
        per_entity: dict[str, list[AlertEvent]] = defaultdict(list)
        for event in items:
            per_entity[event.entity].append(event)
        for series in per_entity.values():
            series.sort(key=lambda e: e.started_at)
            for prev, cur in zip(series, series[1:]):
                if prev.ended_at and _minutes(cur.started_at - prev.ended_at) <= flap_gap_min:
                    flaps += 1

        acked = sum(1 for e in items if e.acked_at)
        labeled = [e for e in items if e.actionable is not None]
        rows.append({
            "rule": rule,
            "count": len(items),
            "per_day": len(items) / days,
            "entities": len(per_entity),
            "median_duration_min": statistics.median(durations) if durations else None,
            "short_share": short_share,
            "flap_share": flaps / len(items),
            "ack_rate": acked / len(items),
            "actionable_rate": (sum(1 for e in labeled if e.actionable) / len(labeled)) if labeled else None,
            "labeled": len(labeled),
        })

    for row in rows:
        row["noisy"] = bool(
            row["count"] >= MIN_RULE_COUNT
            and ((row["short_share"] or 0) >= 0.5 or row["flap_share"] >= 0.5 or row["ack_rate"] < 0.2)
        )
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _bursts(events: list[AlertEvent], gap_min: float) -> dict:
    ordered = sorted(events, key=lambda e: e.started_at)
    groups: list[list[AlertEvent]] = []
    for event in ordered:
        if groups and _minutes(event.started_at - groups[-1][-1].started_at) <= gap_min:
            groups[-1].append(event)
        else:
            groups.append([event])
    bursts = [g for g in groups if len(g) >= 3 and len({e.entity for e in g}) >= 2]
    in_burst = sum(len(g) for g in bursts)
    singles = len(events) - in_burst
    incidents_after = singles + len(bursts)

    # Etiket (incident_id) varsa: gruplama gerçek incident'ı mı yakaladı, yoksa gürültüyü mü grupladı?
    labeled = None
    if any(e.incident_id for e in events):
        incident_bursts = [g for g in bursts if sum(1 for e in g if e.incident_id) / len(g) >= 0.5]
        burst_of: dict[str, set[int]] = defaultdict(set)
        for idx, g in enumerate(bursts):
            for e in g:
                if e.incident_id:
                    burst_of[e.incident_id].add(idx)
        all_incidents = {e.incident_id for e in events if e.incident_id}
        labeled = {
            "incidents_total": len(all_incidents),
            "incident_bursts": len(incident_bursts),
            "noise_bursts": len(bursts) - len(incident_bursts),
            "incidents_split_across_bursts": sum(1 for v in burst_of.values() if len(v) > 1),
        }
    return {
        "labeled": labeled,
        "bursts": len(bursts),
        "alerts_in_bursts": in_burst,
        "share_in_bursts": in_burst / len(events) if events else 0.0,
        "avg_burst_size": (in_burst / len(bursts)) if bursts else 0.0,
        "max_burst_size": max((len(g) for g in bursts), default=0),
        "reduction_ratio": (len(events) / incidents_after) if incidents_after else None,
    }


def _timing_by_severity(events: list[AlertEvent]) -> list[dict]:
    rows = []
    for severity in ("critical", "high", "warning", "info"):
        group = [e for e in events if e.severity == severity]
        if not group:
            continue
        mtta = [_minutes(e.acked_at - e.started_at) for e in group if e.acked_at]
        mttr = [_minutes(e.ended_at - e.started_at) for e in group if e.ended_at]
        rows.append({
            "severity": severity, "count": len(group),
            "mtta_n": len(mtta), "mtta_median_min": percentile(mtta, 0.5), "mtta_p90_min": percentile(mtta, 0.9),
            "mttr_n": len(mttr), "mttr_median_min": percentile(mttr, 0.5), "mttr_p90_min": percentile(mttr, 0.9),
        })
    return rows


def analyze(events: list[AlertEvent], tz_offset_hours: float = 3.0, short_min: float = 5.0,
            flap_gap_min: float = 10.0, burst_gap_min: float = 5.0) -> dict:
    if not events:
        raise ValueError("analiz için en az bir alert olayı gerekir")
    events = sorted(events, key=lambda e: e.started_at)
    first = events[0].started_at
    last = max((e.ended_at or e.started_at) for e in events)
    days = max((last - first).total_seconds() / 86400.0, 1.0)

    rules = _rule_stats(events, days, short_min, flap_gap_min)
    total = len(events)

    running, rules_for_80 = 0, 0
    for row in rules:
        running += row["count"]
        rules_for_80 += 1
        if running / total >= 0.8:
            break
    top_n = max(1, round(len(rules) * 0.1))
    top_share = sum(r["count"] for r in rules[:top_n]) / total

    offset = timedelta(hours=tz_offset_hours)
    night = [e for e in events if e.severity in ("high", "critical")
             and not (7 <= (e.started_at + offset).hour < 22)]

    noisy_rules = [r for r in rules if r["noisy"]]
    noisy_volume = sum(r["count"] for r in noisy_rules)
    labeled = [e for e in events if e.actionable is not None]

    return {
        "window": {"start": first.isoformat(), "end": last.isoformat(), "days": round(days, 2)},
        "totals": {
            "alerts": total, "per_day": total / days, "rules": len(rules),
            "entities": len({e.entity for e in events}),
            "sources": sorted({e.source for e in events}),
            "still_open": sum(1 for e in events if e.ended_at is None),
        },
        "by_severity": {s: sum(1 for e in events if e.severity == s) for s in ("critical", "high", "warning", "info")},
        "pareto": {"rules_for_80pct_volume": rules_for_80, "top10pct_rules_share": top_share, "top_n": top_n},
        "actionable": {
            "labeled": len(labeled),
            "rate": (sum(1 for e in labeled if e.actionable) / len(labeled)) if labeled else None,
        },
        "noise": {
            "noisy_rules": len(noisy_rules), "noisy_volume": noisy_volume,
            "noisy_volume_share": noisy_volume / total,
            "criteria": f"count>={MIN_RULE_COUNT} ve (kısa süreli(<{short_min:g} dk)>=%50 veya tekrar>=%50 veya ack<%20)",
        },
        "timing": _timing_by_severity(events),
        "night_pages": {"count": len(night), "tz_offset_hours": tz_offset_hours,
                        "per_week": len(night) / (days / 7.0)},
        "bursts": _bursts(events, burst_gap_min),
        "rules": rules,
    }


def evaluate_noise_flags(result: dict) -> Optional[dict]:
    """Etiketli veri varsa: davranış-bazlı 'gürültülü' bayrağını insan etiketiyle karşılaştırır (kural bazında)."""
    judged = [r for r in result["rules"] if r["count"] >= MIN_RULE_COUNT and r["actionable_rate"] is not None]
    if not judged:
        return None
    truth = {r["rule"]: r["actionable_rate"] < 0.2 for r in judged}
    flagged = {r["rule"]: r["noisy"] for r in judged}
    tp = sum(1 for k in truth if truth[k] and flagged[k])
    fp = sum(1 for k in truth if not truth[k] and flagged[k])
    fn = sum(1 for k in truth if truth[k] and not flagged[k])
    return {
        "rules_judged": len(judged), "true_noisy": sum(truth.values()),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "missed_rules": sorted(k for k in truth if truth[k] and not flagged[k]),
        "false_alarm_rules": sorted(k for k in truth if not truth[k] and flagged[k]),
    }
