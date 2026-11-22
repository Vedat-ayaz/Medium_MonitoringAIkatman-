# Seri planı (özet)

**Seri:** Monitoring'e AI Katmanı. Kaynaklar: Zabbix, ELK, Prometheus/Grafana. Dil: Türkçe. Kitle: DevOps/SRE.

## Kalite ilkeleri (her yazıda)
1. "Ne işe yaramadı" bölümü zorunlu
2. Her yazı tek başına anlamlı
3. Gerçek (anonimleştirilmiş) veri; sentetik veri açıkça etiketli
4. Rakamlarla konuş: MTTR, doğruluk, token maliyeti, gecikme
5. Satıcıdan bağımsız

## Sezon 1: Doğru eşik, doğru alert, hızlı kök neden
- 1.1 Alarm yorgunluğu: önce ölç (taslak hazır)
- 1.2 Veri hattı: Zabbix, ELK, Prometheus ortak şema ve özet
- 1.3 AI ile doğru eşik değerleri
- 1.4 Alert tasarımı: kime, hangi önem seviyesinde
- 1.5 Hızlı korelasyon
- 1.6 Kök neden ajanı v1

## Sezon 2: Geçmiş çözümlerden güvenli aksiyona
- 2.1 Geçmiş vaka hafızası
- 2.2 Benzer vakadan aksiyon planı
- 2.3 Güvenli yürütme: onay, dry-run, yetki
- 2.4 Değerlendirme, maliyet, gecikme
- 2.5 Kapanış: sonuçlar ve satıcı karşılaştırması

## Ek: yerel (on-prem) model yazısı
Veri gizliliği nedeniyle dışarı çıkamayan şirket verisi için, küçük ve on-prem çalışabilen bir modelin şirket verisiyle fine-tune edilmesi ve büyük modellerle (Claude, GPT) kıyaslanması. Sezon 2, 5. yazı. Ölçülecek: doğruluk, gecikme, kaynak (GPU/RAM) ihtiyacı, maliyet. Bu deney GPU'su olan yerel bir makinede çalıştırılacak.
