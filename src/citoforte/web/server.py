from __future__ import annotations

import html
import importlib
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


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _list_midi_input_ports() -> list[str]:
    try:
        rtmidi = importlib.import_module("rtmidi")
    except ImportError:
        return []

    midi_in: object | None = None
    try:
        midi_in = rtmidi.MidiIn(rtmidi.API_LINUX_ALSA)
    except Exception:
        try:
            midi_in = rtmidi.MidiIn()
        except Exception:
            return []

    try:
        return midi_in.get_ports()
    except Exception:
        return []
    finally:
        del midi_in


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


def _page_html(
    config: MonitorConfig,
    settings_path: Path,
    available_ports: list[str],
    message: str = "",
) -> str:
    escaped_hint = html.escape(config.device_name_hint or "", quote=True)
    escaped_settings_path = html.escape(str(settings_path), quote=True)
    escaped_selected = html.escape(config.selected_device_name or "", quote=True)

    device_options = ['<option value="">Auto / nessuna selezione fissa</option>']
    for port_name in available_ports:
        escaped_name = html.escape(port_name, quote=True)
        selected_attr = ""
        if config.selected_device_name and port_name == config.selected_device_name:
            selected_attr = " selected"
        device_options.append(
            f'<option value="{escaped_name}"{selected_attr}>{escaped_name}</option>'
        )

    if config.selected_device_name and config.selected_device_name not in available_ports:
        device_options.append(
            f'<option value="{escaped_selected}" selected>{escaped_selected} (non connesso)</option>'
        )

    note_options = []
    for idx, note_name in enumerate(NOTE_NAMES):
        selected_attr = " selected" if idx == config.instrument_start_note else ""
        note_options.append(f'<option value="{idx}"{selected_attr}>{note_name}</option>')

    mapping_options = [
        (
            "controller_octave",
            "Usa solo una ottava specifica del controller",
            "Le note fuori da quella ottava vengono ignorate.",
        ),
        (
            "fold_all_octaves",
            "Comprimi tutte le ottave in un'unica ottava",
            "Ogni C del controller suona la stessa nota base dello strumento.",
        ),
    ]

    mapping_rows = []
    for value, title, subtitle in mapping_options:
        checked = " checked" if config.octave_mapping_mode == value else ""
        mapping_rows.append(
            f"""
            <label class=\"radio-card\">
              <input class=\"mapping-mode-radio\" type=\"radio\" name=\"octave_mapping_mode\" value=\"{value}\"{checked}>
              <div>
                <strong>{title}</strong>
                <span>{subtitle}</span>
              </div>
            </label>
            """
        )

    ports_status = "Nessun dispositivo MIDI rilevato al momento."
    if available_ports:
        ports_status = f"Dispositivi MIDI rilevati: {len(available_ports)}"

    controller_label = "Nessun controller MIDI disponibile"
    if config.selected_device_name:
      controller_label = f"Controller selezionato: {config.selected_device_name}"
      if config.selected_device_name not in available_ports:
        controller_label += " (non connesso)"
    elif available_ports:
      controller_label = f"Controller selezionato automaticamente: {available_ports[0]}"

    message_box = ""
    if message:
        message_box = (
            "<div class=\"notice\">"
            f"{html.escape(message)}"
            "</div>"
        )

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
      --surface: #f8fafc;
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
      width: min(840px, 100%);
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
    .controller-mode {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .controller-summary {{
      padding: 10px 12px;
      border-radius: 10px;
      background: #fff;
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 0.95rem;
    }}
    .toggle-button {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      width: fit-content;
      padding: 10px 14px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--border);
      cursor: pointer;
      user-select: none;
    }}
    .toggle-button input {{
      width: 18px;
      height: 18px;
      margin: 0;
    }}
    .hidden {{
      display: none !important;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}
    .section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }}
    .section h2 {{
      margin: 0 0 6px;
      font-size: 1.05rem;
    }}
    .section p {{
      margin-bottom: 12px;
      font-size: 0.92rem;
    }}
    .notice {{
      padding: 10px;
      border-radius: 8px;
      background: #dff6dd;
      color: #1b4332;
      margin-bottom: 16px;
    }}
    .radio-card {{
      margin-top: 8px;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      gap: 10px;
      align-items: flex-start;
      background: #fff;
    }}
    .radio-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.86rem;
      margin-top: 2px;
      font-weight: 400;
    }}
    select {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      font-size: 1rem;
      background: #fff;
    }}
    .muted-line {{
      margin-top: 8px;
      margin-bottom: 0;
      font-size: 0.86rem;
      color: var(--muted);
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
      <div class=\"grid\">
        <section class=\"section\">
          <h2>Settaggi tecnici</h2>
          <p>Selezione del controller e comportamento di discovery.</p>

          <label for=\"poll_interval_seconds\">Intervallo polling (secondi)</label>
          <input id=\"poll_interval_seconds\" name=\"poll_interval_seconds\" type=\"number\" min=\"0.1\" step=\"0.1\" value=\"{config.poll_interval_seconds}\">

          <div class=\"controller-mode\">
            <label class=\"toggle-button\" for=\"controller_auto\">
              <input id=\"controller_auto\" name=\"controller_auto\" type=\"checkbox\" {'checked' if config.selected_device_name is None else ''}>
              <span>Auto</span>
            </label>

            <div id=\"controller-summary\" class=\"controller-summary {'hidden' if config.selected_device_name is not None else ''}\">{html.escape(controller_label)}</div>

            <div id=\"controller-manual-block\" class={'hidden' if config.selected_device_name is None else ''}>
              <label for=\"selected_device_name\">Controller MIDI</label>
              <select id=\"selected_device_name\" name=\"selected_device_name\">
                {''.join(device_options)}
              </select>
              <p class=\"muted-line\">{html.escape(ports_status)}</p>
            </div>
          </div>

          <label for=\"device_name_hint\">Filtro nome dispositivo (substring)</label>
          <input id=\"device_name_hint\" name=\"device_name_hint\" type=\"text\" placeholder=\"es. keystation\" value=\"{escaped_hint}\">
        </section>

        <section class=\"section\">
          <h2>Impostazioni di esecuzione</h2>
          <p>Mapping ottave/note per adattare il controller allo strumento.</p>

          {''.join(mapping_rows)}

          <label for=\"controller_octave\">Ottava controller usata (solo modalita ottava singola)</label>
          <input id=\"controller_octave\" name=\"controller_octave\" type=\"number\" min=\"-1\" max=\"9\" step=\"1\" value=\"{config.controller_octave}\" {'disabled' if config.octave_mapping_mode != 'controller_octave' else ''}>

          <label for=\"instrument_start_note\">Nota di inizio dell'ottava strumento</label>
          <select id=\"instrument_start_note\" name=\"instrument_start_note\">
            {''.join(note_options)}
          </select>

          <label for=\"note_offset_semitones\">Offset semitoni (es. C -> E = +4)</label>
          <input id=\"note_offset_semitones\" name=\"note_offset_semitones\" type=\"number\" min=\"-24\" max=\"24\" step=\"1\" value=\"{config.note_offset_semitones}\">
        </section>
      </div>

      <button class=\"button\" type=\"submit\">Salva</button>
    </form>
    <p class=\"hint\">File impostazioni: {escaped_settings_path}</p>
  </main>
  <script>
    (function () {{
      const autoToggle = document.getElementById('controller_auto');
      const summary = document.getElementById('controller-summary');
      const manualBlock = document.getElementById('controller-manual-block');
      const manualSelect = document.getElementById('selected_device_name');
      const mappingRadios = Array.from(document.querySelectorAll('.mapping-mode-radio'));
      const controllerOctaveInput = document.getElementById('controller_octave');

      function refreshControllerUi() {{
        const autoMode = autoToggle.checked;
        summary.classList.toggle('hidden', !autoMode);
        manualBlock.classList.toggle('hidden', autoMode);
        if (manualSelect) {{
          manualSelect.disabled = autoMode;
        }}
      }}

      function refreshMappingUi() {{
        const controllerModeSelected = mappingRadios.some((radio) => radio.checked && radio.value === 'controller_octave');
        if (controllerOctaveInput) {{
          controllerOctaveInput.disabled = !controllerModeSelected;
        }}
      }}

      autoToggle.addEventListener('change', refreshControllerUi);
      mappingRadios.forEach((radio) => radio.addEventListener('change', refreshMappingUi));
      refreshControllerUi();
      refreshMappingUi();
    }})();
  </script>
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
            available_ports = _list_midi_input_ports()
            body = _page_html(current, store.settings_path, available_ports).encode("utf-8")
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
            controller_auto = "controller_auto" in form
            selected_device_name = None if controller_auto else (
              (form.get("selected_device_name", [""])[0] or "").strip() or None
            )

            try:
                poll_interval_seconds = float(form.get("poll_interval_seconds", ["2.0"])[0])
            except ValueError:
                poll_interval_seconds = 2.0

            if poll_interval_seconds <= 0:
                poll_interval_seconds = 2.0

            auto_discover = controller_auto
            octave_mapping_mode = form.get("octave_mapping_mode", ["controller_octave"])[0]
            if octave_mapping_mode not in {"controller_octave", "fold_all_octaves"}:
                octave_mapping_mode = "controller_octave"

            def _to_int(key: str, fallback: int, min_value: int, max_value: int) -> int:
                try:
                    parsed = int(form.get(key, [str(fallback)])[0])
                except ValueError:
                    parsed = fallback
                return max(min_value, min(max_value, parsed))

            current_config = store.get()
            controller_octave = _to_int("controller_octave", current_config.controller_octave, -1, 9)
            instrument_start_note = _to_int("instrument_start_note", 0, 0, 11)
            note_offset_semitones = _to_int("note_offset_semitones", 0, -24, 24)

            saved = store.save(
                MonitorConfig(
                    device_name_hint=device_name_hint,
                    selected_device_name=selected_device_name,
                    auto_discover=auto_discover,
                    poll_interval_seconds=poll_interval_seconds,
                    octave_mapping_mode=octave_mapping_mode,
                    controller_octave=controller_octave,
                    instrument_octave=current_config.instrument_octave,
                    instrument_start_note=instrument_start_note,
                    note_offset_semitones=note_offset_semitones,
                )
            )

            available_ports = _list_midi_input_ports()
            body = _page_html(
                saved,
                store.settings_path,
                available_ports,
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
