#!/usr/bin/env bash
RUN="${LAB_RUN_DIR:-/tmp/lab-run}"
for pidfile in "$RUN"/*.pid; do
  [ -e "$pidfile" ] || continue
  kill "$(cat "$pidfile")" 2>/dev/null && echo "stopped $(basename "$pidfile" .pid)"
  rm -f "$pidfile"
done
