# Alert sağlık raporu (SENTETİK: izleme + ELK birleşik)

- Pencere: 2026-09-01 - 2026-10-01 (30.73 gün)
- Kaynaklar: elk, synthetic
- Toplam alert: **8413** (273.8/gün), 21 kural, 24 varlık, hâlâ açık: 3
- Önem dağılımı: critical=118, high=180, warning=8112, info=3

## Hacim ve yoğunlaşma
- Hacmin %80'ini üreten kural sayısı: **5** / 21
- En çok tetiklenen ilk %10 kural (2 kural) hacmin %42'ini üretiyor

## Gürültü adayları
- Ölçüt: count>=10 ve (kısa süreli(<5 dk)>=%50 veya tekrar>=%50 veya ack<%20)
- Gürültülü kural: **6**, toplam hacmin %93'i

| Kural | Adet | /gün | Medyan süre (dk) | Kısa süreli | Tekrar | Ack | Aksiyon gerekti | Gürültü? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PingLoss | 1760 | 57.3 | 2.3 | %100 | %8 | %8 | %3 | evet |
| HighLoadAverage | 1740 | 56.6 | 2.2 | %100 | %8 | %9 | %3 | evet |
| HighCPU>80% | 1700 | 55.3 | 2.3 | %100 | %7 | %8 | %3 | evet |
| ErrorLogRate>50/min | 931 | 30.3 | 2.0 | %97 | %7 | %9 | %8 | evet |
| SlowQuery>2s | 867 | 28.2 | 2.0 | %100 | %5 | %7 | %4 | evet |
| AuthFailureBurst | 859 | 28.0 | 2.0 | %100 | %6 | %6 | %6 | evet |
| DiskUsage>80% | 170 | 5.5 | 1001.4 | %0 | %0 | %24 | %10 | - |
| DiskWatermarkLogWarning | 117 | 3.8 | 894.4 | %0 | %0 | %21 | %14 | - |
| QueueBacklog | 46 | 1.5 | 65.9 | %0 | %9 | %74 | %100 | - |
| HealthcheckFailed | 45 | 1.5 | 70.1 | %0 | %4 | %69 | %100 | - |

Aksiyon etiketi olan alert: 8413 (aksiyon gerektiren oranı: %7)

## MTTA ve MTTR (dakika)

| Önem | Adet | MTTA medyan | MTTA p90 | MTTA n | MTTR medyan | MTTR p90 | MTTR n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 118 | 8.8 | 21.4 | 81 | 67.4 | 108.1 | 118 |
| high | 180 | 7.8 | 25.4 | 138 | 66.2 | 110.7 | 177 |
| warning | 8112 | 8.3 | 22.9 | 661 | 2.2 | 3.6 | 8112 |
| info | 3 | 4.2 | 5.3 | 3 | 2245.6 | 3295.3 | 3 |

## Gece sayfalama
- Gece (22:00-07:00, UTC+3) high/critical alert: **120** (haftada 27.3)

## Korelasyon potansiyeli (zaman bazlı, topolojisiz)
- Burst sayısı: 1187, burst içindeki alert: 5664 (%67)
- Ortalama burst boyutu: 4.8, en büyük: 36
- Basit gruplamayla alert sayısı / olay sayısı: **2.1x**
- Etiketle kontrol: 12 gerçek incident var; 12 burst incident'a, **1175 burst yalnızca gürültüye** ait; 0 incident birden fazla burst'e bölündü

## Gürültü bayrağı doğruluğu (insan etiketine karşı, kural bazında)
- Değerlendirilen kural: 15, gerçekte gürültülü: 8
- Precision: %100, recall: %75 (TP=6, FP=0, FN=2)
- Kaçırılan: DiskUsage>80%, DiskWatermarkLogWarning
