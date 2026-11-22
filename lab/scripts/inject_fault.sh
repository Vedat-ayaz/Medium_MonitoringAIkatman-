#!/usr/bin/env bash
# Kontrollü arıza enjeksiyonu (yalnızca lab makinesinde çalıştır).
#   inject_fault.sh cpu [saniye]   -> CPU doygunluğu (HighCPU, HighLoadAverage)
#   inject_fault.sh mem [saniye]   -> bellek baskısı (LowMemoryAvailable)
set -euo pipefail
kind="${1:?kullanım: inject_fault.sh cpu|mem [saniye]}"
secs="${2:-90}"
case "$kind" in
  cpu) stress-ng --cpu "$(nproc)" --timeout "${secs}s" ;;
  mem) stress-ng --vm 1 --vm-bytes 70% --timeout "${secs}s" ;;
  *) echo "bilinmeyen arıza: $kind" >&2; exit 1 ;;
esac
