"""Free Cam: local JPEG relay. Python 3.10+, no external dependencies."""
import argparse
import copy
import hmac
import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from controls import validate_command, validate_snapshot


class ControlConflict(ValueError):
    pass


class Relay(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, token, web_ui=True):
        super().__init__(address, Handler)
        self.token = token
        self.changed = threading.Condition()
        self.frame = None
        self.sequence = 0
        self.last_frame = 0.0
        self.camera = None
        self.last_camera = 0.0
        self.settings = {}
        self.revision = 0
        self.web_ui = web_ui
        self.accept_phone = True

    def publish_native_frame(self, frame):
        """Feed a local camera into the same authenticated OBS stream."""
        with self.changed:
            if self.accept_phone:
                return
            self.frame = frame
            self.last_frame = time.monotonic()
            self.sequence += 1
            self.changed.notify_all()

    def snapshot(self):
        with self.changed:
            return {"connected": time.monotonic() - self.last_frame < 3,
                    "frames": self.sequence,
                    "cameraConnected": time.monotonic() - self.last_camera < 3 and self.camera is not None,
                    "camera": copy.deepcopy(self.camera), "revision": self.revision}

    def exchange_camera(self, data):
        with self.changed:
            report = validate_snapshot(data)
            new_session = self.camera is None or self.camera["session"] != report["session"]
            if report["appliedRevision"] > (0 if new_session else self.revision):
                raise ValueError("Acknowledgement exceeds command revision")
            if new_session:
                self.settings = {}
                self.revision = 0
            self.camera = report
            self.last_camera = time.monotonic()
            return {"revision": self.revision, "settings": self.settings.copy()}

    def submit_controls(self, data):
        with self.changed:
            if self.camera is None or time.monotonic() - self.last_camera >= 3:
                raise ControlConflict("Camera is offline")
            if not isinstance(data, dict) or data.get("session") != self.camera["session"]:
                raise ControlConflict("Camera changed. Reconnect controls.")
            if type(data.get("revision")) is not int or data["revision"] != self.revision:
                raise ControlConflict("Settings changed. Refresh and try again.")
            patch = validate_command(data.get("settings"), self.camera["capabilities"])
            if ("resolution" in self.settings and self.revision > self.camera["appliedRevision"]
                    and self.settings["resolution"] != self.camera["current"].get("resolution")
                    and "resolution" not in patch):
                raise ControlConflict("Wait for the resolution change to finish")
            # Format changes reset sensor modes/ranges. Do not replay previous manual settings.
            self.settings = patch.copy() if "resolution" in patch else {**self.settings, **patch}
            self.revision += 1
            return {"revision": self.revision}


class Handler(BaseHTTPRequestHandler):
    # Keep pairing keys out of HTTP access logs.
    def log_message(self, *_):
        pass

    def reply(self, status, body=b"", content_type="text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if not supplied:
            supplied = parse_qs(urlsplit(self.path).query).get("key", [""])[0]
        return hmac.compare_digest(supplied.encode(), self.server.token.encode())

    def do_POST(self):
        self.connection.settimeout(5)
        path = urlsplit(self.path).path
        if path not in ("/frame", "/camera", "/controls"):
            return self.reply(404)
        if not self.authorized():
            return self.reply(401, b"Invalid pairing key")
        if path in ("/frame", "/camera") and not self.server.accept_phone:
            return self.reply(409, b"Desktop camera source selected")
        if path != "/frame":
            return self.control_request(path)
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.reply(400)
        if not 4 <= size <= 8_000_000:
            return self.reply(413)
        if self.headers.get("Content-Type") != "image/jpeg":
            return self.reply(415)
        try:
            frame = self.rfile.read(size)
        except (OSError, TimeoutError):
            return
        if len(frame) != size or not frame.startswith(b"\xff\xd8") or not frame.endswith(b"\xff\xd9"):
            return self.reply(400, b"Expected a complete JPEG")
        with self.server.changed:
            self.server.frame = frame
            self.server.last_frame = time.monotonic()
            self.server.sequence += 1
            self.server.changed.notify_all()
        self.reply(204)

    def control_request(self, path):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 65536:
                return self.reply(413)
            if self.headers.get("Content-Type") != "application/json":
                return self.reply(415)
            raw = self.rfile.read(size)
            if len(raw) != size:
                return self.reply(400)
            data = json.loads(raw, parse_constant=lambda _: None)
            with self.server.changed:
                if path == "/camera":
                    response = self.server.exchange_camera(data)
                else:
                    response = self.server.submit_controls(data)
            self.reply(200, json.dumps(response, allow_nan=False).encode(), "application/json")
        except ControlConflict as error:
            self.reply(409, str(error).encode())
        except (ValueError, TypeError, UnicodeError) as error:
            self.reply(400, str(error).encode())
        except (OSError, TimeoutError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/" and self.server.web_ui:
            return self.reply(200, Path(__file__).with_name("index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/app.js" and self.server.web_ui:
            return self.reply(200, Path(__file__).with_name("app.js").read_bytes(), "text/javascript; charset=utf-8")
        if path not in ("/status", "/stream.mjpg"):
            return self.reply(404)
        if not self.authorized():
            return self.reply(401, b"Invalid pairing key")
        if path == "/status":
            status = self.server.snapshot()
            return self.reply(200, json.dumps(status).encode(), "application/json")
        self.connection.settimeout(5)
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        sequence = -1
        try:
            while True:
                with self.server.changed:
                    fresh = self.server.changed.wait_for(
                        lambda: self.server.sequence != sequence and self.server.frame is not None,
                        timeout=2)
                    if not fresh:
                        # Wake periodically; socket timeout limits slow consumers.
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                        continue
                    frame = self.server.frame
                    sequence = self.server.sequence
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
                self.wfile.flush()
        except (OSError, TimeoutError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    token = secrets.token_hex(8)
    server = Relay((args.host, args.port), token)
    print(f"Preview: http://127.0.0.1:{args.port}", flush=True)
    print(f"Pairing key: {token}", flush=True)
    try:
        addresses = sorted(set(socket.gethostbyname_ex(socket.gethostname())[2]))
        for address in addresses:
            if not address.startswith("127."):
                print(f"iPhone receiver address: http://{address}:{args.port}", flush=True)
    except OSError:
        pass
    print(f"OBS Media Source URL: http://127.0.0.1:{args.port}/stream.mjpg?key={token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
