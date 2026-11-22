"""Zabbix adaptörü (JSON-RPC): event.get ile PROBLEM olayları ve r_eventid ile kapanış zamanı."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from ..schema import AlertEvent, normalize_severity


class ZabbixClient:
    def __init__(self, url: str, user: Optional[str] = None, password: Optional[str] = None,
                 token: Optional[str] = None, timeout: float = 60.0):
        self.url = url.rstrip("/") + ("" if url.rstrip("/").endswith("api_jsonrpc.php") else "/api_jsonrpc.php")
        self.timeout = timeout
        self.token = token       # API token (Zabbix 5.4+): Bearer başlığı
        self.auth: Optional[str] = None  # eski sürümler: user.login sonucu
        self._id = 0
        if not token:
            if not (user and password):
                raise ValueError("token veya kullanıcı/parola gerekir")
            self.auth = self.call("user.login", {"user": user, "password": password}, authenticated=False)

    def call(self, method: str, params: dict, authenticated: bool = True):
        self._id += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._id}
        headers = {"Content-Type": "application/json-rpc"}
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif authenticated and self.auth:
            body["auth"] = self.auth
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        if "error" in payload:
            raise RuntimeError(f"Zabbix API hatası ({method}): {payload['error']}")
        return payload["result"]


def _ts(value: object) -> Optional[datetime]:
    return datetime.fromtimestamp(int(value), tz=timezone.utc) if value not in (None, "", "0", 0) else None


def collect(client: ZabbixClient, hours: float = 24.0) -> list[AlertEvent]:
    time_from = int(time.time() - hours * 3600)
    problems = client.call("event.get", {
        "output": ["eventid", "name", "severity", "clock", "r_eventid", "objectid"],
        "source": 0, "object": 0, "value": 1, "time_from": time_from,
        "selectHosts": ["host"], "select_acknowledges": ["clock"],
        "sortfield": ["clock"], "sortorder": "ASC",
    })

    recovery_ids = [p["r_eventid"] for p in problems if p.get("r_eventid") not in (None, "", "0")]
    recovered: dict[str, int] = {}
    for i in range(0, len(recovery_ids), 500):
        for ev in client.call("event.get", {"output": ["eventid", "clock"], "eventids": recovery_ids[i:i + 500]}):
            recovered[ev["eventid"]] = int(ev["clock"])

    events = []
    for p in problems:
        acks = sorted(int(a["clock"]) for a in p.get("acknowledges", []))
        hosts = [h["host"] for h in p.get("hosts", [])]
        events.append(AlertEvent(
            id=f"zbx:{p['eventid']}", source="zabbix", rule=p["name"],
            entity=",".join(hosts) or "unknown", severity=normalize_severity(p["severity"]),
            started_at=_ts(p["clock"]),
            ended_at=_ts(recovered.get(p.get("r_eventid", "0"))),
            acked_at=_ts(acks[0]) if acks else None,
            labels={"triggerid": str(p.get("objectid", ""))},
        ))
    return events
