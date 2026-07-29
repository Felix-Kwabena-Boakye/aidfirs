import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import AGENT_NAME, AGENT_OS
from usb.detector import get_usb_devices


class AgentHTTPHandler(BaseHTTPRequestHandler):
    """
    Lightweight HTTP Request Handler for local AIDFIRS Forensic Agent.
    Allows Django backend to probe agent health and trigger real-time USB scans.
    """

    def _send_json(self, data, status_code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("", "/health"):
            self._send_json({
                "status": "ok",
                "agent_name": AGENT_NAME,
                "os": AGENT_OS,
                "version": "2.0",
                "message": "AIDFIRS Local Forensic Agent is active"
            })
        elif path in ("/devices", "/scan", "/devices/scan"):
            devices = get_usb_devices()
            self._send_json({
                "status": "success",
                "devices": [d.to_dict() for d in devices],
                "count": len(devices)
            })
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/scan", "/devices/scan", "/devices"):
            devices = get_usb_devices()
            self._send_json({
                "status": "success",
                "devices": [d.to_dict() for d in devices],
                "count": len(devices)
            })
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def log_message(self, format, *args):
        # Suppress noise in agent console
        pass


class ThreadedHTTPServer(HTTPServer):
    """Multi-threaded HTTP Server for non-blocking probes."""
    daemon_threads = True


def start_agent_server(host="127.0.0.1", port=8765):
    """Starts the local agent HTTP server in a background daemon thread."""
    server = ThreadedHTTPServer((host, port), AgentHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Agent Server] Listening on http://{host}:{port}")
    return server
