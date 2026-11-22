# Alert sağlık raporu (SENTETİK ELK, stand-in sunucudan toplandı)

- Pencere: 2026-09-01 - 2026-10-01 (30.5 gün)
- Kaynaklar: elk
- Toplam alert: **2843** (93.2/gün), 8 kural, 23 varlık, hâlâ açık: 0
- Önem dağılımı: critical=44, high=57, warning=2742, info=0

## Hacim ve yoğunlaşma
- Hacmin %80'ini üreten kural sayısı: **3** / 8
- En çok tetiklenen ilk %10 kural (1 kural) hacmin %33'ini üretiyor

## Gürültü adayları
- Ölçüt: count>=10 ve (kısa süreli(<5 dk)>=%50 veya tekrar>=%50 veya ack<%20)
- Gürültülü kural: **3**, toplam hacmin %93'i

| Kural | Adet | /gün | Medyan süre (dk) | Kısa süreli | Tekrar | Ack | Aksiyon gerekti | Gürültü? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| ErrorLogRate>50/min | 931 | 30.5 | 2.0 | %97 | %7 | %9 | %8 | evet |
| SlowQuery>2s | 867 | 28.4 | 2.0 | %100 | %5 | %7 | %4 | evet |
| AuthFailureBurst | 859 | 28.2 | 2.0 | %100 | %6 | %6 | %6 | evet |
| DiskWatermarkLogWarning | 117 | 3.8 | 894.4 | %0 | %0 | %21 | %14 | - |
| UpstreamTimeoutLogs | 34 | 1.1 | 67.7 | %0 | %3 | %76 | %100 | - |
| ConnectionRefusedLogs | 29 | 1.0 | 62.5 | %0 | %3 | %79 | %100 | - |
| OOMKilledLog | 4 | 0.1 | 17.7 | %0 | %0 | %100 | %100 | - |
| TLSHandshakeFailures | 2 | 0.1 | 71.4 | %0 | %0 | %100 | %100 | - |

Aksiyon etiketi olan alert: 2843 (aksiyon gerektiren oranı: %9)

## MTTA ve MTTR (dakika)

| Önem | Adet | MTTA medyan | MTTA p90 | MTTA n | MTTR medyan | MTTR p90 | MTTR n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| critical | 44 | 9.0 | 15.0 | 31 | 83.1 | 107.8 | 44 |
| high | 57 | 8.3 | 20.9 | 41 | 64.4 | 109.5 | 57 |
| warning | 2742 | 8.8 | 25.7 | 196 | 2.1 | 3.3 | 2742 |

## Gece sayfalama
- Gece (22:00-07:00, UTC+3) high/critical alert: **40** (haftada 9.2)

## Korelasyon potansiyeli (zaman bazlı, topolojisiz)
- Burst sayısı: 169, burst içindeki alert: 655 (%23)
- Ortalama burst boyutu: 3.9, en büyük: 14
- Basit gruplamayla alert sayısı / olay sayısı: **1.2x**
- Etiketle kontrol: 12 gerçek incident var; 12 burst incident'a, **157 burst yalnızca gürültüye** ait; 0 incident birden fazla burst'e bölündü

## Gürültü bayrağı doğruluğu (insan etiketine karşı, kural bazında)
- Değerlendirilen kural: 6, gerçekte gürültülü: 4
- Precision: %100, recall: %75 (TP=3, FP=0, FN=1)
- Kaçırılan: DiskWatermarkLogWarning
