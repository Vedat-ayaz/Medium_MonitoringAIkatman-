"""Analiz sonucunu okunabilir Markdown raporuna çevirir."""
from __future__ import annotations

from typing import Optional


def _f(value: Optional[float], digits: int = 1, suffix: str = "") -> str:
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def _pct(value: Optional[float]) -> str:
    return "-" if value is None else f"%{value * 100:.0f}"


def render_markdown(result: dict, evaluation: Optional[dict] = None, top: int = 10, title: str = "Alert sağlık raporu") -> str:
    t, w = result["totals"], result["window"]
    lines = [f"# {title}", ""]
    lines += [
        f"- Pencere: {w['start'][:10]} - {w['end'][:10]} ({w['days']} gün)",
        f"- Kaynaklar: {', '.join(t['sources'])}",
        f"- Toplam alert: **{t['alerts']}** ({t['per_day']:.1f}/gün), {t['rules']} kural, {t['entities']} varlık, hâlâ açık: {t['still_open']}",
        f"- Önem dağılımı: " + ", ".join(f"{k}={v}" for k, v in result["by_severity"].items()),
        "",
        "## Hacim ve yoğunlaşma",
        f"- Hacmin %80'ini üreten kural sayısı: **{result['pareto']['rules_for_80pct_volume']}** / {t['rules']}",
        f"- En çok tetiklenen ilk %10 kural ({result['pareto']['top_n']} kural) hacmin {_pct(result['pareto']['top10pct_rules_share'])}'ini üretiyor",
        "",
        "## Gürültü adayları",
        f"- Ölçüt: {result['noise']['criteria']}",
        f"- Gürültülü kural: **{result['noise']['noisy_rules']}**, toplam hacmin {_pct(result['noise']['noisy_volume_share'])}'i",
        "",
        "| Kural | Adet | /gün | Medyan süre (dk) | Kısa süreli | Tekrar | Ack | Aksiyon gerekti | Gürültü? |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in result["rules"][:top]:
        lines.append(
            f"| {r['rule']} | {r['count']} | {r['per_day']:.1f} | {_f(r['median_duration_min'])} | "
            f"{_pct(r['short_share'])} | {_pct(r['flap_share'])} | {_pct(r['ack_rate'])} | "
            f"{_pct(r['actionable_rate'])} | {'evet' if r['noisy'] else '-'} |"
        )
    a = result["actionable"]
    lines += ["", f"Aksiyon etiketi olan alert: {a['labeled']} (aksiyon gerektiren oranı: {_pct(a['rate'])})", ""]

    lines += ["## MTTA ve MTTR (dakika)", "",
              "| Önem | Adet | MTTA medyan | MTTA p90 | MTTA n | MTTR medyan | MTTR p90 | MTTR n |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in result["timing"]:
        lines.append(f"| {r['severity']} | {r['count']} | {_f(r['mtta_median_min'])} | {_f(r['mtta_p90_min'])} | "
                     f"{r['mtta_n']} | {_f(r['mttr_median_min'])} | {_f(r['mttr_p90_min'])} | {r['mttr_n']} |")

    n, b = result["night_pages"], result["bursts"]
    lines += [
        "", "## Gece sayfalama",
        f"- Gece (22:00-07:00, UTC{n['tz_offset_hours']:+g}) high/critical alert: **{n['count']}** (haftada {n['per_week']:.1f})",
        "", "## Korelasyon potansiyeli (zaman bazlı, topolojisiz)",
        f"- Burst sayısı: {b['bursts']}, burst içindeki alert: {b['alerts_in_bursts']} ({_pct(b['share_in_bursts'])})",
        f"- Ortalama burst boyutu: {b['avg_burst_size']:.1f}, en büyük: {b['max_burst_size']}",
        f"- Basit gruplamayla alert sayısı / olay sayısı: **{_f(b['reduction_ratio'], 1, 'x')}**",
    ]
    if b.get("labeled"):
        lb = b["labeled"]
        lines += [
            f"- Etiketle kontrol: {lb['incidents_total']} gerçek incident var; "
            f"{lb['incident_bursts']} burst incident'a, **{lb['noise_bursts']} burst yalnızca gürültüye** ait; "
            f"{lb['incidents_split_across_bursts']} incident birden fazla burst'e bölündü",
        ]
    if evaluation:
        lines += [
            "", "## Gürültü bayrağı doğruluğu (insan etiketine karşı, kural bazında)",
            f"- Değerlendirilen kural: {evaluation['rules_judged']}, gerçekte gürültülü: {evaluation['true_noisy']}",
            f"- Precision: {_pct(evaluation['precision'])}, recall: {_pct(evaluation['recall'])} "
            f"(TP={evaluation['tp']}, FP={evaluation['fp']}, FN={evaluation['fn']})",
        ]
        if evaluation["missed_rules"]:
            lines.append(f"- Kaçırılan: {', '.join(evaluation['missed_rules'])}")
        if evaluation["false_alarm_rules"]:
            lines.append(f"- Yanlış işaretlenen: {', '.join(evaluation['false_alarm_rules'])}")
    return "\n".join(lines) + "\n"
