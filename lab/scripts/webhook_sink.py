"""Alertmanager webhook alıcısı: gelen her bildirimi ham haliyle JSONL'e yazar."""
import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer


def make_handler(out_path: str):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            record = {"received_at": datetime.now(timezone.utc).isoformat(), "payload": json.loads(body or b"{}")}
            with open(out_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    HTTPServer(("127.0.0.1", args.port), make_handler(args.out)).serve_forever()
