# Monitoring'e AI Katmanı (Medium yazı dizisi)

> **Kod deposu:** https://github.com/Vedat-ayaz/Medium_MonitoringAIkatman-

Zabbix, ELK ve Prometheus/Grafana verisini bir AI katmanıyla birleştirip doğru eşik/alert tasarımı, hızlı korelasyon, kök neden analizi ve geçmiş çözümlerden aksiyon önerisi üreten bir yazı dizisinin kod deposu.

Tam plan: `docs/PLAN.md`. Yazılar: `articles/`.

## Durum

| Yazı | Durum |
| --- | --- |
| 1.1 Alert sağlık raporu | Yazıldı (`articles/medium-ilk-yazi/yazi.md`), kod çalışıyor |
| 1.2 - 2.5 | Planlandı |

## Hızlı başlangıç (bağımlılıksız Python 3.10+)

```bash
python3 -m pytest -q                                   # testler (pip install pytest)
python3 -m alerthealth generate --days 30 --out data/synthetic/events_30d.jsonl   # SENTETİK veri
python3 -m alerthealth analyze data/synthetic/events_30d.jsonl --out reports/rapor.md

# ELK: sentetik doküman üret, stand-in sunucuyu başlat, HTTP ile topla
python3 -m alerthealth generate-elk --out data/synthetic/elk_alerts_30d.ndjson
python3 lab/elk/stub_es.py --now 2026-10-02T00:00:00Z --load alerts-synthetic=data/synthetic/elk_alerts_30d.ndjson &
python3 -m alerthealth collect elk --url http://127.0.0.1:9200 --index "alerts-*" --hours 744 --preset synthetic-elk --out data/synthetic/elk_events_30d.jsonl
```

Kendi ortamından toplama:

```bash
python3 -m alerthealth collect prometheus --url http://prometheus:9090 --hours 168 --out data/real/prom.jsonl
python3 -m alerthealth collect zabbix --url http://zabbix --token $ZBX_TOKEN --hours 168 --out data/real/zbx.jsonl
python3 -m alerthealth collect elk --url https://es:9200 --index alerts-* --api-key $ES_KEY \
  --field-map '{"rule":"rule.name","entity":"host.name"}' --out data/real/elk.jsonl
cat data/real/*.jsonl > data/real/all.jsonl
python3 -m alerthealth analyze data/real/all.jsonl --out reports/gercek.md
```

`data/real/` ve `data/lab/` `.gitignore` içindedir: gerçek veri repoya girmez.

## Klasörler

- `alerthealth/`: ortak şema, adaptörler (Prometheus, Zabbix, Elasticsearch), metrikler, rapor, sentetik üretici, CLI
- `lab/`: Prometheus + Alertmanager lab yapılandırması, arıza enjeksiyonu, Zabbix chroot kurulumu, ELK stand-in sunucusu (bkz. `docs/ENVIRONMENT.md`)
- `data/samples/`: gerçek lab alarmları (7) ve sentetik 30 günlük veri
- `reports/`: örnek rapor çıktıları
- `articles/`: yazılar
- `tests/`: birim testleri

## Dürüstlük notları

- Sentetik veri gerçek değildir ve her yerde öyle etiketlenir.
- ELK adaptörü yalnızca Elasticsearch API'siyle uyumlu bir stand-in sunucuya (`lab/elk/stub_es.py`) karşı test edildi; gerçek Elasticsearch kümesine karşı değil.
- Zabbix lab'ı 5.0.17 (eski sürüm) ile çalışıyor.
