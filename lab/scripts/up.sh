#!/usr/bin/env bash
# Lab ortamını (Prometheus + node_exporter + Alertmanager + webhook alıcısı) arka planda başlatır.
# Gereksinim (Ubuntu/Debian): apt install prometheus prometheus-node-exporter prometheus-alertmanager stress-ng
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN="${LAB_RUN_DIR:-/tmp/lab-run}"
mkdir -p "$RUN/prom-data" "$RUN/am-data" "$RUN/logs" "$ROOT/data/lab"

start() { local name=$1; shift; nohup "$@" >"$RUN/logs/$name.log" 2>&1 & echo $! >"$RUN/$name.pid"; echo "started $name (pid $(cat "$RUN/$name.pid"))"; }

start node_exporter prometheus-node-exporter --web.listen-address=127.0.0.1:9100
start webhook python3 "$ROOT/lab/scripts/webhook_sink.py" --port 5001 --out "$ROOT/data/lab/alertmanager_webhooks.jsonl"
start alertmanager prometheus-alertmanager --config.file="$ROOT/lab/prometheus/alertmanager.yml" \
  --storage.path="$RUN/am-data" --web.listen-address=127.0.0.1:9093 --cluster.listen-address=
start prometheus prometheus --config.file="$ROOT/lab/prometheus/prometheus.yml" \
  --storage.tsdb.path="$RUN/prom-data" --web.listen-address=127.0.0.1:9090

# ELK stand-in (GERÇEK Elasticsearch değil): sentetik ELK alarmları varsa yükle
ELK_DATA="$ROOT/data/synthetic/elk_alerts_30d.ndjson"
if [ -f "$ELK_DATA" ]; then
  start stub_es python3 "$ROOT/lab/elk/stub_es.py" --port 9200 --now 2026-10-02T00:00:00Z --load "alerts-synthetic=$ELK_DATA"
fi

echo "Prometheus: http://127.0.0.1:9090  Alertmanager: http://127.0.0.1:9093"
