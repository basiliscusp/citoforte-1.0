from __future__ import annotations

import html
import shutil
import ssl
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from citoforte.config import MonitorConfig
from citoforte.runtime_settings import RuntimeSettingsStore


def _generate_self_signed_cert(cert_path: Path, key_path: Path) -> bool:
    openssl_binary = shutil.which("openssl")
    if openssl_binary is None:
        return False

    cert_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        openssl_binary,
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-sha256",
        "-days",
        "3650",
        "-nodes",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-subj",
        "/CN=citoforte.local",
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return False

    return cert_path.exists() and key_path.exists()


def _page_html(config: MonitorConfig, settings_path: Path, message: str = "") -> str:
    escaped_hint = html.escape(config.device_name_hint or "", quote=True)
    escaped_settings_path = html.escape(str(settings_path), quote=True)
    message_box = ""
    if message:
        message_box = f'<div style="padding:10px;border-radius:8px;background:#dff6dd;color:#1b4332;margin-bottom:16px;">{html.escape(message)}</div>'

    return f"""<!doctype html>
<html lang=\"it\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>CITOFORTE Config</title>
  <style>
    :root {{
      --bg: #f4f8fb;
      --card: #ffffff;
      --text: #16324f;
      --accent: #0f766e;
      --accent-hover: #115e59;
      --muted: #5b6b7a;
      --border: #d7e1ea;
    }}
    body {{
      margin: 0;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: linear-gradient(135deg, #ecf4fb 0%, #f8fbf2 100%);
      color: var(--text);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      box-sizing: border-box;
    }}
    .card {{
      width: min(560px, 100%);
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 14px 42px rgba(15, 50, 80, 0.12);
      padding: 24px;
    }}
    h1 {{
      margin-top: 0;
      margin-bottom: 8px;
      font-size: 1.5rem;
    }}
    p {{
      margin-top: 0;
      color: var(--muted);
    }}
    label {{
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
      margin-top: 14px;
    }}
    input[type=text],
    input[type=number] {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      font-size: 1rem;
    }}
    .row {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
    }}
    .button {{
      margin-top: 18px;
      border: 0;
      border-radius: 10px;
      padding: 10px 16px;
      font-size: 1rem;
      font-weight: 700;
      color: #fff;
      background: var(--accent);
      cursor: pointer;
    }}
    .button:hover {{
      background: var(--accent-hover);
    }}
    .hint {{
      margin-top: 16px;
      font-size: 0.9rem;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <main class=\"card\">
    <h1>CITOFORTE Configurazione</h1>
    <p>Le modifiche vengono salvate in modo permanente e applicate subito anche durante l'esecuzione.</p>
    {message_box}
    <form method=\"post\" action=\"/save\">
      <label for=\"device_name_hint\">Filtro dispositivo (substring)</label>
      <input id=\"device_name_hint\" name=\"device_name_hint\" type=\"text\" placeholder=\"es. keystation\" value=\"{escaped_hint}\">

      <label for=\"poll_interval_seconds\">Intervallo polling (secondi)</label>
      <input id=\"poll_interval_seconds\" name=\"poll_interval_seconds\" type=\"number\" min=\"0.1\" step=\"0.1\" value=\"{config.poll_interval_seconds}\">

      <div class=\"row\">
        <input id=\"auto_discover\" name=\"auto_discover\" type=\"checkbox\" {'checked' if config.auto_discover else ''}>
        <label for=\"auto_discover\" style=\"margin:0;\">Auto-discovery porte</label>
      </div>

      <button class=\"button\" type=\"submit\">Salva</button>
    </form>
    <p class=\"hint\">File impostazioni: {escaped_settings_path}</p>
  </main>
</body>
</html>
"""


def _build_handler(store: RuntimeSettingsStore) -> type[BaseHTTPRequestHandler]:
    class ConfigHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            current = store.refresh_if_changed()
            body = _page_html(current, store.settings_path).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length).decode("utf-8")
            form = parse_qs(payload, keep_blank_values=True)

            device_name_hint = (form.get("device_name_hint", [""])[0] or "").strip() or None

            try:
                poll_interval_seconds = float(form.get("poll_interval_seconds", ["2.0"])[0])
            except ValueError:
                poll_interval_seconds = 2.0

            if poll_interval_seconds <= 0:
                poll_interval_seconds = 2.0

            auto_discover = "auto_discover" in form

            saved = store.save(
                MonitorConfig(
                    device_name_hint=device_name_hint,
                    auto_discover=auto_discover,
                    poll_interval_seconds=poll_interval_seconds,
                )
            )

            body = _page_html(
                saved,
                store.settings_path,
                message="Configurazione salvata e applicata immediatamente.",
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return ConfigHandler


def _start_http_server(host: str, port: int, handler_cls: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer | None:
    try:
        server = ThreadingHTTPServer((host, port), handler_cls)
    except OSError as exc:
        print(f"[web] Impossibile avviare HTTP su {host}:{port} ({exc})")
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[web] HTTP attivo su http://{host}:{port}")
    return server


def _start_https_server(
    host: str,
    port: int,
    cert_path: Path,
    key_path: Path,
    handler_cls: type[BaseHTTPRequestHandler],
) -> ThreadingHTTPServer | None:
    if not cert_path.exists() or not key_path.exists():
        generated = _generate_self_signed_cert(cert_path, key_path)
        if generated:
            print(f"[web] Certificato self-signed generato in {cert_path}")
        else:
            print("[web] HTTPS disabilitato: certificato non disponibile e openssl assente/errore")
            return None

    try:
        server = ThreadingHTTPServer((host, port), handler_cls)
    except OSError as exc:
        print(f"[web] Impossibile avviare HTTPS su {host}:{port} ({exc})")
        return None

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    server.socket = context.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[web] HTTPS attivo su https://{host}:{port}")
    return server


def start_config_servers(
    store: RuntimeSettingsStore,
    host: str = "0.0.0.0",
    http_port: int = 80,
    https_port: int = 443,
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> list[ThreadingHTTPServer]:
    cert = cert_path or Path("config/certs/cert.pem")
    key = key_path or Path("config/certs/key.pem")
    handler_cls = _build_handler(store)

    running: list[ThreadingHTTPServer] = []

    http_server = _start_http_server(host, http_port, handler_cls)
    if http_server is not None:
        running.append(http_server)

    https_server = _start_https_server(host, https_port, cert, key, handler_cls)
    if https_server is not None:
        running.append(https_server)

    if not running:
        print("[web] Nessun server web avviato")

    return running