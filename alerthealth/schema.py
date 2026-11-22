"""Ortak alert olay şeması: Zabbix, Prometheus ve ELK verisi bu forma çevrilir."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

SEVERITIES = ("info", "warning", "high", "critical")

_SEVERITY_ALIASES = {
    "none": "info", "not classified": "info", "information": "info", "info": "info",
    "low": "info", "notice": "info",
    "warning": "warning", "warn": "warning", "average": "warning", "medium": "warning",
    "high": "high", "error": "high", "major": "high",
    "critical": "critical", "disaster": "critical", "page": "critical", "fatal": "critical",
}


def normalize_severity(value: object) -> str:
    """Kaynak araçtaki önem seviyesini info/warning/high/critical'a indirger."""
    if value is None:
        return "warning"
    text = str(value).strip().lower()
    if text in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[text]
    if text.isdigit():  # Zabbix: 0..5
        return {0: "info", 1: "info", 2: "warning", 3: "warning", 4: "high", 5: "critical"}.get(int(text), "warning")
    return "warning"


def parse_ts(value: object) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # epoch saniye veya milisaniye
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        return parse_ts(int(text))
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass
class AlertEvent:
    id: str
    source: str            # zabbix | prometheus | elk | synthetic
    rule: str              # trigger / alert kuralı adı
    entity: str            # host, instance veya servis
    severity: str          # info | warning | high | critical
    started_at: datetime
    ended_at: Optional[datetime] = None   # None: hâlâ açık
    acked_at: Optional[datetime] = None   # ilk insan müdahalesi/onayı
    actionable: Optional[bool] = None     # insan etiketi: aksiyon gerektirdi mi
    incident_id: Optional[str] = None     # bağlı incident (varsa)
    labels: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        def iso(ts: Optional[datetime]) -> Optional[str]:
            return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None

        return {
            "id": self.id, "source": self.source, "rule": self.rule, "entity": self.entity,
            "severity": self.severity, "started_at": iso(self.started_at),
            "ended_at": iso(self.ended_at), "acked_at": iso(self.acked_at),
            "actionable": self.actionable, "incident_id": self.incident_id, "labels": self.labels,
        }

    @classmethod
    def from_json(cls, data: dict) -> "AlertEvent":
        return cls(
            id=str(data["id"]), source=str(data.get("source", "unknown")), rule=str(data["rule"]),
            entity=str(data.get("entity", "unknown")), severity=normalize_severity(data.get("severity")),
            started_at=parse_ts(data["started_at"]), ended_at=parse_ts(data.get("ended_at")),
            acked_at=parse_ts(data.get("acked_at")), actionable=data.get("actionable"),
            incident_id=data.get("incident_id"), labels=dict(data.get("labels") or {}),
        )


def write_jsonl(path: str | Path, events: Iterable[AlertEvent]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_json(), ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[AlertEvent]:
    events: list[AlertEvent] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(AlertEvent.from_json(json.loads(line)))
    return events


def iter_jsonl(path: str | Path) -> Iterator[AlertEvent]:
    yield from read_jsonl(path)
