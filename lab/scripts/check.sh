#!/usr/bin/env bash
# Lab servislerinin sağlık kontrolü: süreç + uç nokta. Çıkış kodu: tümü ayaktaysa 0.
fail=0
chk() { # ad, komut
  local name=$1; shift
  if out=$("$@" 2>/dev/null) && [ -n "$out" ]; then printf "UP    %-22s %s\n" "$name" "$(echo "$out" | head -c 70)"; else printf "DOWN  %-22s\n" "$name"; fail=1; fi
}
chk prometheus        curl -s -m 4 http://127.0.0.1:9090/-/ready
chk alertmanager      curl -s -m 4 http://127.0.0.1:9093/-/healthy
chk node_exporter     bash -c "curl -s -m 4 http://127.0.0.1:9100/metrics | grep -m1 '^node_load1'"
chk webhook_sink      bash -c "pgrep -f webhook_sink.py >/dev/null && echo running"
chk elk_stub          bash -c "curl -s -m 4 'http://127.0.0.1:9200/alerts-*/_count'"
chk zabbix_api        bash -c "curl -s -m 6 -H 'Content-Type: application/json-rpc' -d '{\"jsonrpc\":\"2.0\",\"method\":\"apiinfo.version\",\"params\":[],\"id\":1}' http://127.0.0.1:8081/api_jsonrpc.php"
chk zabbix_server     bash -c "pgrep -x zabbix_server >/dev/null && echo running"
chk zabbix_agent      bash -c "pgrep -x zabbix_agentd >/dev/null && echo running"
exit $fail
