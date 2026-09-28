"""Trivial local HTTP server used to test whether oTree's headless CLI bot
runner can perform blocking network I/O inside PlayerBot.play_round().

Each request sleeps DELAY_SECONDS to simulate an LLM API call, then returns
a JSON payload. We log every request with a timestamp and thread name so we
can tell whether requests arrive serially (single-threaded bot runner) or
concurrently.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY_SECONDS = float(os.environ.get("MF_TEST_SERVER_DELAY", "0.5"))
LOG_PATH = os.path.join(os.path.dirname(__file__), "network_test_server_log.jsonl")

_lock = threading.Lock()
_counter = {"n": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence default stderr logging

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {"raw": body.decode(errors="replace")}

        t_recv = time.time()
        with _lock:
            _counter["n"] += 1
            seq = _counter["n"]

        time.sleep(DELAY_SECONDS)

        t_done = time.time()
        record = {
            "seq": seq,
            "thread": threading.current_thread().name,
            "received_at": t_recv,
            "responded_at": t_done,
            "payload": payload,
        }
        with _lock, open(LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")

        resp = json.dumps({"contribution": 10 + (seq % 5), "seq": seq}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)


if __name__ == "__main__":
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)
    port = int(os.environ.get("MF_TEST_SERVER_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"listening on 127.0.0.1:{port}, delay={DELAY_SECONDS}s")
    server.serve_forever()
