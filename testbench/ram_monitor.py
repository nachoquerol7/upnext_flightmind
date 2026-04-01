#!/usr/bin/env python3
"""HTTP JSON de RSS por procesos ROS2 relacionados (testbench MemoryPanel)."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import psutil
except ImportError:
    psutil = None


def _match_proc(p):
    name = (p.info.get("name") or "") or ""
    cmd = " ".join(p.info.get("cmdline") or [])
    blob = name + " " + cmd
    keys = ("mission_fsm", "rosbridge", "daidalus", "fdir", "nav2")
    return any(k in blob for k in keys)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        procs = []
        if psutil:
            for p in psutil.process_iter(["pid", "name", "memory_info", "cmdline"]):
                try:
                    if not _match_proc(p):
                        continue
                    rss = p.info.get("memory_info")
                    mb = round(rss.rss / 1e6, 1) if rss else 0.0
                    procs.append({"name": p.info.get("name") or "?", "pid": p.info.get("pid"), "mb": mb})
                except (psutil.Error, TypeError, AttributeError):
                    continue
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(procs).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("localhost", 9091), Handler).serve_forever()
