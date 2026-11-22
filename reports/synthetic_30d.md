# Alert sağlık raporu (SENTETİK 30 gün)

- Pencere: 2026-09-01 - 2026-10-01 (30.73 gün)
- Kaynaklar: synthetic
- Toplam alert: **5570** (181.3/gün), 13 kural, 24 varlık, hâlâ açık: 3
- Önem dağılımı: critical=74, high=123, warning=5370, info=3

## Hacim ve yoğunlaşma
- Hacmin %80'ini üreten kural sayısı: **3** / 13
- En çok tetiklenen ilk %10 kural (1 kural) hacmin %32'ini üretiyor

## Gürültü adayları
- Ölçüt: count>=10 ve (kısa süreli(<5 dk)>=%50 veya tekrar>=%50 veya ack<%20)
- Gürültülü kural: **3**, toplam hacmin %93'i

| Kural | Adet | /gün | Medyan süre (dk) | Kısa süreli | Tekrar | Ack | Aksiyon gerekti | Gürültü? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PingLoss | 1760 | 57.3 | 2.3 | %100 | %8 | %8 | %3 | evet |
| HighLoadAverage | 1740 | 56.6 | 2.2 | %100 | %8 | %9 | %3 | evet |
| HighCPU>80% | 1700 | 55.3 | 2.3 | %100 | %7 | %8 | %3 | evet |
| DiskUsage>80% | 170 | 5.5 | 1001.4 | %0 | %0 | %24 | %10 | - |
| QueueBacklog | 46 | 1.5 | 65.9 | %0 | %9 | %74 | %100 | - |
| HealthcheckFailed | 45 | 1.5 | 70.1 | %0 | %4 | %69 | %100 | - |
| LatencyP95>1s | 45 | 1.5 | 70.5 | %0 | %7 | %64 | %100 | - |
| HTTP5xxRate>5% | 34 | 1.1 | 65.4 | %0 | %3 | %79 | %100 | - |
| ServiceDown | 12 | 0.4 | 38.3 | %0 | %0 | %100 | %100 | - |
| DBReplicationLag | 8 | 0.3 | 50.8 | %0 | %0 | %100 | %100 | - |

Aksiyon etiketi olan alert: 5570 (aksiyon gerektiren oranı: %7)

## MTTA ve MTTR (dakika)

| Önem | Adet | MTTA medyan | MTTA p90 | MTTA n | MTTR medyan | MTTR p90 | MTTR n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 74 | 7.5 | 21.9 | 50 | 66.6 | 108.6 | 74 |
| high | 123 | 7.6 | 25.6 | 97 | 67.9 | 110.8 | 120 |
| warning | 5370 | 8.2 | 21.8 | 465 | 2.3 | 3.8 | 5370 |
| info | 3 | 4.2 | 5.3 | 3 | 2245.6 | 3295.3 | 3 |

## Gece sayfalama
- Gece (22:00-07:00, UTC+3) high/critical alert: **80** (haftada 18.2)

## Korelasyon potansiyeli (zaman bazlı, topolojisiz)
- Burst sayısı: 601, burst içindeki alert: 2492 (%45)
- Ortalama burst boyutu: 4.1, en büyük: 27
- Basit gruplamayla alert sayısı / olay sayısı: **1.5x**
- Etiketle kontrol: 12 gerçek incident var; 12 burst incident'a, **589 burst yalnızca gürültüye** ait; 0 incident birden fazla burst'e bölündü

## Gürültü bayrağı doğruluğu (insan etiketine karşı, kural bazında)
- Değerlendirilen kural: 9, gerçekte gürültülü: 4
- Precision: %100, recall: %75 (TP=3, FP=0, FN=1)
- Kaçırılan: DiskUsage>80%
