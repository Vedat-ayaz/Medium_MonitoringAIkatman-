# Alert sağlık raporu (LAB, canlı: Prometheus + Zabbix)

- Pencere: 2026-11-22 - 2026-11-22 (1.0 gün)
- Kaynaklar: prometheus, zabbix
- Toplam alert: **7** (7.0/gün), 5 kural, 2 varlık, hâlâ açık: 0
- Önem dağılımı: critical=0, high=0, warning=7, info=0

## Hacim ve yoğunlaşma
- Hacmin %80'ini üreten kural sayısı: **4** / 5
- En çok tetiklenen ilk %10 kural (1 kural) hacmin %29'ini üretiyor

## Gürültü adayları
- Ölçüt: count>=10 ve (kısa süreli(<5 dk)>=%50 veya tekrar>=%50 veya ack<%20)
- Gürültülü kural: **0**, toplam hacmin %0'i

| Kural | Adet | /gün | Medyan süre (dk) | Kısa süreli | Tekrar | Ack | Aksiyon gerekti | Gürültü? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| HighCPU | 2 | 2.0 | 1.1 | %100 | %50 | %0 | - | - |
| HighLoadAverage | 2 | 2.0 | 1.5 | %100 | %50 | %0 | - | - |
| Zabbix server: Utilization of timer processes over 75% | 1 | 1.0 | 1.0 | %100 | %0 | %0 | - | - |
| Lab: Many running processes | 1 | 1.0 | 2.0 | %100 | %0 | %0 | - | - |
| Lab: High load per CPU | 1 | 1.0 | 1.8 | %100 | %0 | %0 | - | - |

Aksiyon etiketi olan alert: 0 (aksiyon gerektiren oranı: -)

## MTTA ve MTTR (dakika)

| Önem | Adet | MTTA medyan | MTTA p90 | MTTA n | MTTR medyan | MTTR p90 | MTTR n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| warning | 7 | - | - | 0 | 1.5 | 1.9 | 7 |

## Gece sayfalama
- Gece (22:00-07:00, UTC+3) high/critical alert: **0** (haftada 0.0)

## Korelasyon potansiyeli (zaman bazlı, topolojisiz)
- Burst sayısı: 1, burst içindeki alert: 7 (%100)
- Ortalama burst boyutu: 7.0, en büyük: 7
- Basit gruplamayla alert sayısı / olay sayısı: **7.0x**
