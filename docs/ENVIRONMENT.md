# Test ortamı: nerede ne çalışıyor?

Hedef: Mac'i yormadan test ortamını uzaktaki geçici bir Linux makinesinde çalıştırmak. Kod ve yapılandırma bu klasörde, **çalışan servisler uzak makinede**.

## Uzak makinede çalışan (doğrulandı)

| Bileşen | Sürüm | Nasıl kuruldu | Durum |
| --- | --- | --- | --- |
| Prometheus | 2.45.3 | Ubuntu 24.04 apt | Çalıştı, gerçek alarm üretti |
| node_exporter | 1.7.0 | apt | Çalıştı |
| Alertmanager | 0.26.0 | apt | Çalıştı, webhook'a bildirim gönderdi |
| Zabbix server + agent | 5.0.17 | Ubuntu 22.04 (jammy) paketleri, debootstrap chroot (`lab/zabbix/chroot_setup.sh`) | Çalıştı, API girişi ve alarm toplama doğrulandı |
| PostgreSQL | 14 | chroot içinde apt | Zabbix veritabanı |
| Zabbix web/API | nginx + php-fpm 8.1 | chroot içinde, `127.0.0.1:8081` | Çalıştı |

## ELK: stand-in (gerçek Elasticsearch DEĞİL)

| Bileşen | Ne | Durum |
| --- | --- | --- |
| `lab/elk/stub_es.py` | Elasticsearch API'siyle uyumlu sahte sunucu (`_search` + scroll, range, `_bulk`, `_doc`), `127.0.0.1:9200` | Çalıştı, `alerts-synthetic` indeksinde 2.843 sentetik doküman |
| `alerthealth generate-elk` | ECS benzeri SENTETİK log alarmı dokümanları (aynı 12 incident'a bağlı) | `data/synthetic/elk_alerts_30d.ndjson` |
| Uçtan uca test | `collect elk` HTTP ile topladı, orijinalle saniye çözünürlüğünde birebir aynı | `tests/test_stub_es.py` |

Gerçek Elasticsearch/Kibana/Logstash kurulamadı: Elastic depoları, Docker Hub ve Maven erişilemiyor; Ubuntu apt, PyPI ve conda-forge'da sunucu yok (conda-forge'daki `elasticsearch` yalnızca Python istemcisi). Stand-in kimlik doğrulama, aggregation, sort ve sürüm farklarını SINAMAZ.

## Çalıştırılamayan

- **Gerçek Elasticsearch / Kibana / Logstash** (yukarıya bakın).
- **Grafana:** depo erişimi yok. Dizi için zorunlu değil; Prometheus yeterli.
- **Docker ile compose:** imaj depolarına erişim yok.

## Kalıcılık uyarısı

Geçici makinede arka planda çalışan servisler, oturum bittikten kısa süre sonra durdurulur. Bu yüzden her şey betikle yeniden kurulabilir olmalı:

```bash
bash lab/scripts/up.sh                       # Prometheus, Alertmanager, node_exporter, webhook alıcısı, ELK stand-in
                                             # (stand-in için önce: python3 -m alerthealth generate-elk --out data/synthetic/elk_alerts_30d.ndjson)
bash lab/zabbix/chroot_setup.sh              # Zabbix (chroot önceden debootstrap ile kurulu olmalı)
python3 lab/zabbix/provision.py              # host'u etkinleştir, item ve trigger ekle
bash lab/scripts/inject_fault.sh cpu 120     # kontrollü arıza
```

Chroot sıfırlanırsa: `debootstrap --variant=minbase jammy /opt/zbx-jammy http://archive.ubuntu.com/ubuntu`, sonra jammy deposundan `postgresql zabbix-server-pgsql zabbix-frontend-php zabbix-agent php8.1-fpm php8.1-pgsql nginx` kurulur.

## Lab parolaları

`zbxlab` (veritabanı) ve `Admin/zabbix` (web) yalnızca bu geçici lab içindir; hiçbir gerçek sisteme ait değildir.
