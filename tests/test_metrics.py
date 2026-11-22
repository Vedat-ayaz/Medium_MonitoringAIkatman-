from datetime import datetime, timedelta, timezone

from alerthealth.metrics import analyze, evaluate_noise_flags, percentile
from alerthealth.schema import AlertEvent, normalize_severity

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def ev(i, rule, entity, start_min, dur_min, severity="warning", ack_min=None, actionable=None):
    start = T0 + timedelta(minutes=start_min)
    return AlertEvent(
        id=str(i), source="t", rule=rule, entity=entity, severity=severity, started_at=start,
        ended_at=start + timedelta(minutes=dur_min) if dur_min is not None else None,
        acked_at=start + timedelta(minutes=ack_min) if ack_min is not None else None,
        actionable=actionable,
    )


def test_percentile_and_severity():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([], 0.5) is None
    assert normalize_severity("5") == "critical" and normalize_severity("Average") == "warning"


def test_flapping_rule_is_noisy_and_scored_against_labels():
    events = []
    for i in range(12):  # 12 kısa, art arda tekrar eden alarm, ack yok, aksiyon gerekmedi
        events.append(ev(i, "Flap", "a", i * 20, 2, actionable=False))
    for i in range(12):  # 12 uzun süreli, ack edilen, aksiyon gerektiren alarm
        events.append(ev(100 + i, "Real", "b", i * 300, 60, severity="high", ack_min=5, actionable=True))
    result = analyze(events)
    flags = {r["rule"]: r["noisy"] for r in result["rules"]}
    assert flags == {"Flap": True, "Real": False}
    evaluation = evaluate_noise_flags(result)
    assert evaluation["precision"] == 1.0 and evaluation["recall"] == 1.0


def test_burst_grouping_and_timing():
    events = [ev(i, f"R{i}", f"h{i}", i, 30, severity="critical", ack_min=4) for i in range(6)]
    events.append(ev(99, "Lonely", "x", 600, 10))
    result = analyze(events)
    assert result["bursts"]["bursts"] == 1 and result["bursts"]["alerts_in_bursts"] == 6
    assert result["bursts"]["reduction_ratio"] == 7 / 2
    critical = next(r for r in result["timing"] if r["severity"] == "critical")
    assert critical["mtta_median_min"] == 4 and critical["mttr_median_min"] == 30


def test_night_pages_use_local_time():
    night = ev(1, "N", "a", 0, 5, severity="high")      # 12:00 UTC -> 15:00 yerel: gündüz
    night.started_at = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)  # 02:00 yerel (UTC+3)
    day = ev(2, "D", "a", 0, 5, severity="high")
    result = analyze([night, day], tz_offset_hours=3)
    assert result["night_pages"]["count"] == 1


def test_labeled_bursts_separate_incident_from_noise():
    events = [ev(i, f"I{i}", f"h{i}", i, 30, severity="critical") for i in range(5)]
    for e in events:
        e.incident_id = "INC-1"
    events += [ev(50 + i, f"N{i}", f"n{i}", 1000 + i, 2) for i in range(4)]  # gürültü kümesi, incident değil
    labeled = analyze(events)["bursts"]["labeled"]
    assert labeled == {"incidents_total": 1, "incident_bursts": 1, "noise_bursts": 1,
                       "incidents_split_across_bursts": 0}
