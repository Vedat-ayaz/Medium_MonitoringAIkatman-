"""Komut satırı: generate | generate-elk | collect | analyze | tokens."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .metrics import analyze, evaluate_noise_flags
from .report import render_markdown
from .schema import read_jsonl, write_jsonl


def _cmd_generate(args: argparse.Namespace) -> int:
    from .synthetic import generate

    events = generate(days=args.days, hosts=args.hosts, seed=args.seed)
    count = write_jsonl(args.out, events)
    print(f"{count} SENTETİK alert yazıldı: {args.out}")
    return 0


def _cmd_generate_elk(args: argparse.Namespace) -> int:
    import json as _json

    from .synthetic_elk import event_to_doc, generate_elk

    events = generate_elk(days=args.days, hosts=args.hosts, seed=args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(_json.dumps(event_to_doc(event), ensure_ascii=False) + "\n")
    print(f"{len(events)} SENTETİK ELK alarm dokümanı yazıldı (NDJSON): {args.out}")
    return 0


def _cmd_collect(args: argparse.Namespace) -> int:
    if args.source == "prometheus":
        from .adapters import prometheus
        events = prometheus.collect(args.url, hours=args.hours)
    elif args.source == "zabbix":
        from .adapters import zabbix
        client = zabbix.ZabbixClient(args.url, user=args.user, password=args.password, token=args.token)
        events = zabbix.collect(client, hours=args.hours)
    else:
        from .adapters import elastic
        mapping = json.loads(args.field_map) if args.field_map else None
        if args.preset == "synthetic-elk":
            from .synthetic_elk import FIELD_MAP
            mapping = {**FIELD_MAP, **(mapping or {})}
        events = elastic.collect(args.url, args.index, field_map=mapping, hours=args.hours, api_key=args.api_key)
    count = write_jsonl(args.out, events)
    print(f"{count} alert olayı toplandı ({args.source}): {args.out}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    events = read_jsonl(args.input)
    result = analyze(events, tz_offset_hours=args.tz)
    evaluation = evaluate_noise_flags(result)
    markdown = render_markdown(result, evaluation, title=args.title)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(markdown, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({"result": result, "evaluation": evaluation}, ensure_ascii=False,
                                              indent=2, default=str), encoding="utf-8")
    print(markdown)
    return 0


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """KABA tahmin (karakter/3.5). Gerçek sayım için modelin token sayacı kullanılmalı."""
    return round(len(text) / chars_per_token)


def _cmd_tokens(args: argparse.Namespace) -> int:
    raw = Path(args.raw).read_text(encoding="utf-8")
    summary = Path(args.summary).read_text(encoding="utf-8")
    raw_t, sum_t = estimate_tokens(raw), estimate_tokens(summary)
    print(f"ham veri: {len(raw):,} karakter ~ {raw_t:,} token (tahmin)")
    print(f"özet    : {len(summary):,} karakter ~ {sum_t:,} token (tahmin)")
    print(f"oran    : {raw_t / max(sum_t, 1):.0f}x")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="alerthealth", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="sentetik alert geçmişi üret (GERÇEK DEĞİL)")
    g.add_argument("--days", type=int, default=30)
    g.add_argument("--hosts", type=int, default=24)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--out", required=True)
    g.set_defaults(func=_cmd_generate)

    ge = sub.add_parser("generate-elk", help="sentetik ELK alarm dokümanları üret (GERÇEK DEĞİL)")
    ge.add_argument("--days", type=int, default=30)
    ge.add_argument("--hosts", type=int, default=24)
    ge.add_argument("--seed", type=int, default=42)
    ge.add_argument("--out", required=True)
    ge.set_defaults(func=_cmd_generate_elk)

    c = sub.add_parser("collect", help="bir monitoring kaynağından alert olaylarını topla")
    c.add_argument("source", choices=["prometheus", "zabbix", "elk"])
    c.add_argument("--url", required=True)
    c.add_argument("--hours", type=float, default=24.0)
    c.add_argument("--out", required=True)
    c.add_argument("--user")
    c.add_argument("--password")
    c.add_argument("--token")
    c.add_argument("--index", help="elk: alert kayıtlarının indeksi")
    c.add_argument("--field-map", help='elk: JSON, ör. {"rule":"rule.name"}')
    c.add_argument("--api-key")
    c.add_argument("--preset", choices=["synthetic-elk"], help="elk: hazır alan eşlemesi (sentetik doküman şeması)")
    c.set_defaults(func=_cmd_collect)

    a = sub.add_parser("analyze", help="alert sağlık raporu üret")
    a.add_argument("input")
    a.add_argument("--out")
    a.add_argument("--json")
    a.add_argument("--tz", type=float, default=3.0, help="UTC farkı (saat), gece hesabı için")
    a.add_argument("--title", default="Alert sağlık raporu")
    a.set_defaults(func=_cmd_analyze)

    t = sub.add_parser("tokens", help="ham veri ile özetin token boyutunu (tahmini) karşılaştır")
    t.add_argument("raw")
    t.add_argument("summary")
    t.set_defaults(func=_cmd_tokens)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
