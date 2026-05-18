#!/usr/bin/env python3
"""Local browser UI for the Codex Enhancer installer."""

from __future__ import annotations

import html
import json
import secrets
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.install_enhancer import (
    InstallPlan,
    apply_install_plan,
    build_install_plan,
    build_overwrite_confirmation_message,
    build_pack_management_plan,
    build_upgrade_plan,
    build_workflow_management_plan,
)
from scripts.install_enhancer_gui import (
    MODE_CHOICES,
    OPERATION_CHOICES,
    SPEC_KIT_COMMAND_SURFACE_CHOICES,
    SPEC_KIT_MODE_CHOICES,
    SPEC_KIT_SCRIPT_CHOICES,
    UTILITY_HARNESS_MODE_CHOICES,
    UTILITY_HARNESS_UPGRADE_MODE_CHOICES,
    action_verb,
    build_completion_message,
    build_plan_preview,
    open_product_readme,
    progress_total,
    requires_confirmation,
)
from scripts.stack_packs import PackSelection, selected_pack_names


BROWSER_TITLE = "Codex Enhancer Installer"
TOKEN_HEADER = "X-Codex-Enhancer-Token"
IDLE_SHUTDOWN_SECONDS = 20 * 60


def _choices_to_payload(choices: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in choices]


def _string_value(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _bool_value(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be true or false.")


def _choice_value(
    payload: dict[str, Any],
    key: str,
    choices: tuple[tuple[str, str], ...],
    default: str,
) -> str:
    value = _string_value(payload, key, default)
    allowed_values = {choice_value for _label, choice_value in choices}
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"{key} must be one of: {allowed}.")
    return value


def _selected_names(payload: dict[str, Any]) -> tuple[str, ...] | None:
    if "selected_packs" not in payload:
        return None
    raw_selected = payload["selected_packs"]
    if raw_selected is None:
        return ()
    if not isinstance(raw_selected, list):
        raise ValueError("selected_packs must be a list.")
    selected: list[str] = []
    for item in raw_selected:
        if not isinstance(item, str):
            raise ValueError("selected_packs entries must be strings.")
        selected.append(item)
    return tuple(selected)


def _target_path(raw_target: str) -> Path:
    target_text = raw_target.strip().strip('"').strip("'")
    parsed = urlparse(target_text)
    if parsed.scheme == "file":
        target_text = unquote(parsed.path)
        if parsed.netloc:
            target_text = f"//{parsed.netloc}{target_text}"
        elif len(target_text) > 2 and target_text[0] == "/" and target_text[2] == ":":
            target_text = target_text[1:]
    return Path(target_text)


def _utility_harness_mode(payload: dict[str, Any], *, upgrade: bool) -> str | None:
    choices = UTILITY_HARNESS_UPGRADE_MODE_CHOICES if upgrade else UTILITY_HARNESS_MODE_CHOICES
    default = UTILITY_HARNESS_UPGRADE_MODE_CHOICES[0][1] if upgrade else UTILITY_HARNESS_MODE_CHOICES[0][1]
    value = _choice_value(payload, "utility_harness_mode", choices, default)
    return None if value == "preserve" else value


def build_plan_from_browser_payload(payload: dict[str, Any]) -> InstallPlan:
    """Build the same installer plan the GUI would build from browser form data."""

    raw_target = _string_value(payload, "target").strip()
    if not raw_target:
        raise ValueError("Enter a target repository path before reviewing.")

    operation = _choice_value(payload, "operation", OPERATION_CHOICES, "install")
    mode = _choice_value(payload, "mode", MODE_CHOICES, "auto")
    spec_kit_mode = _choice_value(payload, "spec_kit_mode", SPEC_KIT_MODE_CHOICES, "auto")
    spec_kit_script = _choice_value(payload, "spec_kit_script", SPEC_KIT_SCRIPT_CHOICES, "auto")
    spec_kit_command_surface = _choice_value(
        payload,
        "spec_kit_command_surface",
        SPEC_KIT_COMMAND_SURFACE_CHOICES,
        "auto",
    )
    spec_kit_version = _string_value(payload, "spec_kit_version").strip() or None
    selected_names = _selected_names(payload)
    target = _target_path(raw_target)

    if operation == "upgrade-enhancer":
        return build_upgrade_plan(
            target,
            set_packs=selected_names,
            spec_kit_mode=spec_kit_mode,
            spec_kit_script=spec_kit_script,
            spec_kit_command_surface=spec_kit_command_surface,
            spec_kit_version=spec_kit_version,
            utility_harness_mode=_utility_harness_mode(payload, upgrade=True),
            utility_harness_install_dependencies=_bool_value(
                payload,
                "utility_harness_dependencies",
            ),
        )

    if operation == "manage-workflows":
        return build_workflow_management_plan(
            target,
            set_workflows=selected_names,
            require_changes=False,
        )

    if operation == "manage-packs":
        return build_pack_management_plan(
            target,
            set_packs=selected_names,
            require_changes=False,
        )

    refresh_generated = operation == "refresh-generated"
    return build_install_plan(
        target,
        mode=mode,
        force=_bool_value(payload, "force") if not refresh_generated else False,
        refresh_generated=refresh_generated,
        use_recommended_packs=selected_names is None and not refresh_generated,
        include_packs=selected_names or (),
        spec_kit_mode=spec_kit_mode if not refresh_generated else None,
        spec_kit_script=spec_kit_script,
        spec_kit_command_surface=spec_kit_command_surface,
        spec_kit_version=spec_kit_version,
        utility_harness_mode=(
            _utility_harness_mode(payload, upgrade=False) if not refresh_generated else None
        ),
        utility_harness_install_dependencies=(
            _bool_value(payload, "utility_harness_dependencies")
            if not refresh_generated
            else False
        ),
    )


def _selection_payload(selection: PackSelection) -> dict[str, Any]:
    return {
        "name": selection.pack.name,
        "label": selection.pack.label,
        "description": selection.pack.description,
        "selected": selection.selected,
        "recommended": selection.recommended,
        "detected": selection.detected,
        "reasons": list(selection.reasons),
        "use_when": list(selection.pack.guidance.use_when),
        "adds": list(selection.pack.guidance.adds),
        "skip_when": list(selection.pack.guidance.skip_when),
    }


def plan_to_browser_payload(
    plan: InstallPlan,
    *,
    plan_id: int | None = None,
    status: str = "Plan ready.",
) -> dict[str, Any]:
    selections = plan.workflow_selections if plan.operation == "manage-workflows" else plan.pack_selections
    return {
        "ok": True,
        "plan_id": plan_id,
        "status": status,
        "operation": plan.operation,
        "action": action_verb(plan),
        "preview": build_plan_preview(plan),
        "requires_confirmation": requires_confirmation(plan),
        "confirmation_message": (
            build_overwrite_confirmation_message(plan) if requires_confirmation(plan) else ""
        ),
        "progress_total": progress_total(plan),
        "selection_kind": "workflow" if plan.operation == "manage-workflows" else "stack",
        "selection_interactive": plan.operation != "refresh-generated",
        "selected_names": list(selected_pack_names(selections)),
        "selections": [_selection_payload(selection) for selection in selections],
    }


@dataclass
class BrowserGuiState:
    token: str
    current_plan: InstallPlan | None = None
    current_plan_id: int = 0
    progress_log: list[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def touch(self) -> None:
        with self.lock:
            self.last_seen = time.monotonic()

    def state_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "title": BROWSER_TITLE,
            "operation_choices": _choices_to_payload(OPERATION_CHOICES),
            "mode_choices": _choices_to_payload(MODE_CHOICES),
            "spec_kit_mode_choices": _choices_to_payload(SPEC_KIT_MODE_CHOICES),
            "spec_kit_script_choices": _choices_to_payload(SPEC_KIT_SCRIPT_CHOICES),
            "spec_kit_command_surface_choices": _choices_to_payload(
                SPEC_KIT_COMMAND_SURFACE_CHOICES
            ),
            "utility_harness_mode_choices": _choices_to_payload(UTILITY_HARNESS_MODE_CHOICES),
            "utility_harness_upgrade_mode_choices": _choices_to_payload(
                UTILITY_HARNESS_UPGRADE_MODE_CHOICES
            ),
        }

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan = build_plan_from_browser_payload(payload)
        with self.lock:
            self.current_plan = plan
            self.current_plan_id += 1
            self.progress_log = []
            plan_id = self.current_plan_id
        return plan_to_browser_payload(plan, plan_id=plan_id)

    def apply(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan_id = int(payload.get("plan_id", 0))
        with self.lock:
            plan = self.current_plan
            if plan is None or plan_id != self.current_plan_id:
                raise ValueError("Review the current plan before applying it.")

        if requires_confirmation(plan) and not _bool_value(payload, "confirmed"):
            raise ValueError(build_overwrite_confirmation_message(plan))

        progress_log: list[str] = []

        def on_progress(current: int, total: int, message: str) -> None:
            progress_log.append(f"{current}/{total} {message}")

        apply_install_plan(
            plan,
            progress_callback=on_progress,
            allow_dirty=_bool_value(payload, "allow_dirty"),
        )

        readme_warning = ""
        try:
            open_product_readme()
        except OSError as error:  # pragma: no cover - platform opener failure
            readme_warning = f"The install finished, but the README could not be opened: {error}"

        with self.lock:
            self.progress_log = progress_log

        response = plan_to_browser_payload(
            plan,
            plan_id=plan_id,
            status=f"{action_verb(plan).capitalize()} complete.",
        )
        response.update(
            {
                "completion_message": build_completion_message(plan),
                "progress_log": progress_log,
                "readme_warning": readme_warning,
            }
        )
        return response


class BrowserInstallerServer(ThreadingHTTPServer):
    state: BrowserGuiState


class BrowserInstallerRequestHandler(BaseHTTPRequestHandler):
    server: BrowserInstallerServer

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            if not self._is_authorized(parsed.query):
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "error": "The installer link token is invalid."},
                )
                return
            self._send_html(render_index(self.server.state.token))
            return

        if parsed.path == "/api/state":
            if not self._is_authorized(parsed.query):
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "error": "The installer session token is invalid."},
                )
                return
            self._send_json(HTTPStatus.OK, self.server.state.state_payload())
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found."})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._is_authorized(parsed.query):
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"ok": False, "error": "The installer session token is invalid."},
            )
            return

        try:
            payload = self._read_json()
            if parsed.path == "/api/review":
                self._send_json(HTTPStatus.OK, self.server.state.review(payload))
                return
            if parsed.path == "/api/apply":
                self._send_json(HTTPStatus.OK, self.server.state.apply(payload))
                return
            if parsed.path == "/api/ping":
                self._send_json(HTTPStatus.OK, {"ok": True, "status": "Installer active."})
                return
            if parsed.path == "/api/shutdown":
                self._send_json(HTTPStatus.OK, {"ok": True, "status": "Closing installer."})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return
        except Exception as error:  # pragma: no cover - defensive local UI boundary
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": f"Installer error: {error}"},
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found."})

    def _is_authorized(self, query: str) -> bool:
        query_token = parse_qs(query).get("token", [""])[0]
        header_token = self.headers.get(TOKEN_HEADER, "")
        token = header_token or query_token
        authorized = secrets.compare_digest(token, self.server.state.token)
        if authorized:
            self.server.state.touch()
        return authorized

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ValueError("Content-Length must be a number.") from error
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length)
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON: {error}") from error
        if not isinstance(parsed, dict):
            raise ValueError("JSON request body must be an object.")
        return parsed

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_browser_gui_server(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    token: str | None = None,
) -> tuple[BrowserInstallerServer, str]:
    state = BrowserGuiState(token=token or secrets.token_urlsafe(24))
    server = BrowserInstallerServer((host, port), BrowserInstallerRequestHandler)
    server.state = state
    url = f"http://{host}:{server.server_address[1]}/?token={state.token}"
    return server, url


def serve_browser_gui(*, open_browser: bool = True) -> int:
    server, url = create_browser_gui_server()
    threading.Thread(target=_shutdown_when_idle, args=(server,), daemon=True).start()
    if open_browser:
        webbrowser.open(url)
    print(f"Codex Enhancer browser installer: {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual server stop
        return 130
    finally:
        server.server_close()
    return 0


def _shutdown_when_idle(server: BrowserInstallerServer) -> None:
    while True:
        time.sleep(30)
        with server.state.lock:
            idle_seconds = time.monotonic() - server.state.last_seen
        if idle_seconds >= IDLE_SHUTDOWN_SECONDS:
            server.shutdown()
            return


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if any(arg not in {"--no-browser"} for arg in args):
        print("Usage: python scripts/install_enhancer_web_gui.py [--no-browser]")
        return 2
    return serve_browser_gui(open_browser="--no-browser" not in args)


def render_index(token: str) -> str:
    return (
        HTML_TEMPLATE.replace("__TOKEN__", html.escape(token, quote=True))
        .replace("__CSS__", CSS)
        .replace("__JS__", JAVASCRIPT)
    )


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codex Enhancer Installer</title>
  <style>__CSS__</style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">Codex Enhancer</p>
      <h1>Installer</h1>
    </div>
    <div id="status" class="status" role="status">Ready</div>
  </header>

  <main class="workspace">
    <section class="panel controls" aria-label="Installer settings">
      <div class="field">
        <label for="target">Target repository path</label>
        <input id="target" type="text" spellcheck="false" placeholder="D:\\Projects\\target-repo or file:///D:/Projects/target-repo">
      </div>

      <div class="field">
        <label for="operation">Operation</label>
        <select id="operation"></select>
      </div>

      <div class="grid two">
        <div class="field">
          <label for="mode">Repo mode</label>
          <select id="mode"></select>
        </div>
        <label class="checkline">
          <input id="force" type="checkbox">
          <span>Overwrite conflicts</span>
        </label>
      </div>

      <div class="divider"></div>

      <div class="grid two">
        <div class="field">
          <label for="spec-kit-mode">Spec Kit</label>
          <select id="spec-kit-mode"></select>
        </div>
        <div class="field">
          <label for="spec-kit-version">Spec Kit ref</label>
          <input id="spec-kit-version" type="text" spellcheck="false" placeholder="latest">
        </div>
      </div>

      <div class="grid two">
        <div class="field">
          <label for="spec-kit-script">Script flavor</label>
          <select id="spec-kit-script"></select>
        </div>
        <div class="field">
          <label for="spec-kit-surface">Command surface</label>
          <select id="spec-kit-surface"></select>
        </div>
      </div>

      <div class="divider"></div>

      <div class="grid two">
        <div class="field">
          <label for="utility-harness-mode">Utility Harness</label>
          <select id="utility-harness-mode"></select>
        </div>
        <label class="checkline">
          <input id="utility-harness-dependencies" type="checkbox">
          <span>Install helper dependencies</span>
        </label>
      </div>

      <label class="checkline dirty">
        <input id="allow-dirty" type="checkbox">
        <span>Allow unrelated git changes</span>
      </label>

      <label id="confirm-row" class="checkline confirm hidden">
        <input id="confirm" type="checkbox">
        <span>Confirm overwrite actions</span>
      </label>

      <div class="actions">
        <button id="review" type="button">Review Plan</button>
        <button id="apply" type="button" disabled>Apply</button>
        <button id="quit" type="button" class="secondary">Quit</button>
      </div>
    </section>

    <section class="panel preview" aria-label="Plan preview">
      <div class="panel-header">
        <h2>Preview</h2>
        <span id="progress">0 steps</span>
      </div>
      <pre id="preview-output">Enter a target path and review the plan.</pre>
    </section>

    <aside class="panel selections" aria-label="Pack selection">
      <div class="panel-header">
        <h2 id="selection-title">Guidance Packs</h2>
        <span id="selection-count">0 selected</span>
      </div>
      <div id="selection-list" class="selection-list">
        <p class="muted">Selections appear after review.</p>
      </div>
      <div id="completion" class="completion hidden"></div>
      <ol id="progress-log" class="progress-log"></ol>
    </aside>
  </main>

  <script>window.CODEX_ENHANCER_TOKEN = "__TOKEN__";</script>
  <script>__JS__</script>
</body>
</html>
"""


CSS = r"""
:root {
  color-scheme: light;
  --bg: #f5f2ea;
  --ink: #18211f;
  --muted: #64706d;
  --line: #d8d0c1;
  --panel: #fffdf8;
  --panel-strong: #f0eadf;
  --teal: #0f766e;
  --teal-dark: #115e59;
  --amber: #b7791f;
  --danger: #9f1239;
  --shadow: 0 16px 38px rgba(36, 29, 14, 0.12);
}

* {
  box-sizing: border-box;
}

body {
  min-width: 320px;
  margin: 0;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.12), transparent 32%),
    linear-gradient(315deg, rgba(183, 121, 31, 0.14), transparent 30%),
    var(--bg);
  color: var(--ink);
  font-family: "Aptos", "Segoe UI", Verdana, sans-serif;
}

.topbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  padding: 24px clamp(16px, 3vw, 36px) 16px;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--teal-dark);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: clamp(2rem, 4vw, 3.2rem);
  line-height: 0.95;
}

h2 {
  font-size: 1rem;
}

.status {
  max-width: min(460px, 50vw);
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 253, 248, 0.84);
  color: var(--muted);
  font-size: 0.9rem;
  box-shadow: 0 8px 18px rgba(36, 29, 14, 0.08);
}

.status.error {
  border-color: rgba(159, 18, 57, 0.35);
  color: var(--danger);
}

.status.success {
  border-color: rgba(15, 118, 110, 0.35);
  color: var(--teal-dark);
}

.workspace {
  display: grid;
  grid-template-columns: minmax(280px, 390px) minmax(360px, 1fr) minmax(280px, 420px);
  gap: 16px;
  min-height: calc(100vh - 116px);
  padding: 0 clamp(16px, 3vw, 36px) 28px;
}

.panel {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 253, 248, 0.92);
  box-shadow: var(--shadow);
}

.controls,
.selections {
  align-self: start;
  max-height: calc(100vh - 136px);
  overflow: auto;
}

.controls {
  padding: 16px;
}

.preview {
  display: flex;
  min-height: 460px;
  flex-direction: column;
  overflow: hidden;
}

.selections {
  padding: 0 0 12px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(240, 234, 223, 0.62);
}

.panel-header span {
  color: var(--muted);
  font-size: 0.84rem;
}

.field {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

label,
.checkline span {
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
}

input[type="text"],
select {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 0.94rem;
  padding: 8px 10px;
}

input[type="text"]:focus,
select:focus,
button:focus-visible {
  outline: 3px solid rgba(15, 118, 110, 0.22);
  outline-offset: 2px;
}

.grid.two {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.checkline {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  margin: 0 0 12px;
}

.checkline input {
  width: 18px;
  height: 18px;
  accent-color: var(--teal);
}

.dirty,
.confirm {
  align-items: flex-start;
}

.confirm {
  padding: 10px;
  border: 1px solid rgba(183, 121, 31, 0.45);
  border-radius: 8px;
  background: rgba(183, 121, 31, 0.1);
}

.divider {
  height: 1px;
  margin: 4px 0 14px;
  background: var(--line);
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  position: sticky;
  bottom: 0;
  padding-top: 12px;
  background: linear-gradient(transparent, var(--panel) 20%);
}

button {
  min-height: 40px;
  border: 0;
  border-radius: 8px;
  background: var(--teal);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-size: 0.92rem;
  font-weight: 800;
  padding: 8px 14px;
}

button:hover {
  background: var(--teal-dark);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

button.secondary {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
}

button.secondary:hover {
  background: var(--panel-strong);
}

#preview-output {
  flex: 1;
  margin: 0;
  overflow: auto;
  padding: 16px;
  background: #171f1d;
  color: #edf7f2;
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 0.86rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

.selection-list {
  display: grid;
  gap: 10px;
  padding: 12px;
}

.selection-item {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}

.selection-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 9px;
  align-items: start;
}

.selection-row input {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  accent-color: var(--teal);
}

.selection-name {
  color: var(--ink);
  font-size: 0.94rem;
  font-weight: 800;
}

.selection-meta {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}

.selection-detail {
  margin: 8px 0 0 27px;
  color: #38433f;
  font-size: 0.84rem;
  line-height: 1.42;
}

.selection-detail strong {
  color: var(--teal-dark);
}

.completion {
  margin: 0 12px 12px;
  padding: 12px;
  border: 1px solid rgba(15, 118, 110, 0.35);
  border-radius: 8px;
  background: rgba(15, 118, 110, 0.08);
  white-space: pre-wrap;
}

.progress-log {
  margin: 0 12px;
  padding-left: 24px;
  color: var(--muted);
  font-size: 0.82rem;
}

.muted {
  margin: 0;
  color: var(--muted);
}

.hidden {
  display: none;
}

@media (max-width: 1160px) {
  .workspace {
    grid-template-columns: minmax(280px, 380px) minmax(360px, 1fr);
  }

  .selections {
    grid-column: 1 / -1;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .topbar {
    align-items: start;
    flex-direction: column;
  }

  .status {
    max-width: 100%;
  }

  .workspace,
  .grid.two {
    grid-template-columns: 1fr;
  }

  .controls,
  .selections {
    max-height: none;
  }

  .actions {
    grid-template-columns: 1fr;
  }
}
"""


JAVASCRIPT = r"""
const token = window.CODEX_ENHANCER_TOKEN;
let appState = null;
let currentPlan = null;
let selectionsKnown = false;

const byId = (id) => document.getElementById(id);

function setStatus(message, kind = "") {
  const status = byId("status");
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

function fillSelect(select, choices, fallbackValue) {
  const previous = select.value || fallbackValue;
  select.replaceChildren();
  for (const choice of choices) {
    const option = document.createElement("option");
    option.value = choice.value;
    option.textContent = choice.label;
    select.appendChild(option);
  }
  const values = choices.map((choice) => choice.value);
  select.value = values.includes(previous) ? previous : fallbackValue;
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Codex-Enhancer-Token": token,
    ...(options.headers || {}),
  };
  const response = await fetch(path, {...options, headers});
  const body = await response.json();
  if (!response.ok || body.ok === false) {
    throw new Error(body.error || "Installer request failed.");
  }
  return body;
}

function syncOperationControls() {
  if (!appState) {
    return;
  }
  const operation = byId("operation").value;
  const isRefresh = operation === "refresh-generated";
  const isManage = operation === "manage-packs" || operation === "manage-workflows";
  const isUpgrade = operation === "upgrade-enhancer";
  const utilityChoices = isUpgrade
    ? appState.utility_harness_upgrade_mode_choices
    : appState.utility_harness_mode_choices;

  byId("mode").disabled = isRefresh || isManage || isUpgrade;
  byId("force").disabled = isRefresh || isManage || isUpgrade;
  byId("spec-kit-mode").disabled = isRefresh || isManage;
  byId("spec-kit-script").disabled = isRefresh || isManage;
  byId("spec-kit-surface").disabled = isRefresh || isManage;
  byId("spec-kit-version").disabled = isRefresh || isManage;

  fillSelect(
    byId("utility-harness-mode"),
    utilityChoices,
    utilityChoices[0].value,
  );
  byId("utility-harness-mode").disabled = isRefresh || isManage;
  syncUtilityDependencyControl();
}

function syncUtilityDependencyControl() {
  const utilityMode = byId("utility-harness-mode").value;
  byId("utility-harness-dependencies").disabled = utilityMode !== "install";
  if (utilityMode !== "install") {
    byId("utility-harness-dependencies").checked = false;
  }
}

function collectPayload({includeSelections = selectionsKnown} = {}) {
  const payload = {
    target: byId("target").value.trim(),
    operation: byId("operation").value,
    mode: byId("mode").value,
    force: byId("force").checked,
    allow_dirty: byId("allow-dirty").checked,
    spec_kit_mode: byId("spec-kit-mode").value,
    spec_kit_script: byId("spec-kit-script").value,
    spec_kit_command_surface: byId("spec-kit-surface").value,
    spec_kit_version: byId("spec-kit-version").value.trim(),
    utility_harness_mode: byId("utility-harness-mode").value,
    utility_harness_dependencies: byId("utility-harness-dependencies").checked,
  };
  if (includeSelections) {
    payload.selected_packs = Array.from(
      document.querySelectorAll("[data-selection-name]"),
    )
      .filter((input) => input.checked)
      .map((input) => input.dataset.selectionName);
  }
  return payload;
}

function resetPlan() {
  currentPlan = null;
  selectionsKnown = false;
  byId("apply").disabled = true;
  byId("confirm").checked = false;
  byId("confirm-row").classList.add("hidden");
  byId("completion").classList.add("hidden");
  byId("completion").textContent = "";
  byId("progress-log").replaceChildren();
}

function renderSelections(plan) {
  const list = byId("selection-list");
  list.replaceChildren();
  const selections = plan.selections || [];
  const selectedCount = selections.filter((selection) => selection.selected).length;
  byId("selection-count").textContent = `${selectedCount} selected`;
  byId("selection-title").textContent =
    plan.selection_kind === "workflow" ? "Workflow Packs" : "Stack Packs";

  if (!selections.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No packs are available for this operation.";
    list.appendChild(empty);
    return;
  }

  for (const selection of selections) {
    const item = document.createElement("section");
    item.className = "selection-item";

    const row = document.createElement("label");
    row.className = "selection-row";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selection.selected;
    checkbox.disabled = !plan.selection_interactive;
    checkbox.dataset.selectionName = selection.name;
    checkbox.addEventListener("change", () => {
      selectionsKnown = true;
      reviewPlan();
    });

    const content = document.createElement("div");
    const title = document.createElement("div");
    title.className = "selection-name";
    title.textContent = `${selection.label} (${selection.name})`;
    const meta = document.createElement("p");
    meta.className = "selection-meta";
    const recommendation = selection.recommended ? "Recommended" : "Optional";
    meta.textContent = `${recommendation}: ${selection.reasons.join("; ") || "manual review"}`;
    content.append(title, meta);
    row.append(checkbox, content);

    const detail = document.createElement("div");
    detail.className = "selection-detail";
    detail.innerHTML = [
      `<strong>Does:</strong> ${escapeHtml(selection.description)}`,
      `<strong>Enable:</strong> ${escapeHtml(selection.use_when.join("; "))}`,
      `<strong>Adds:</strong> ${escapeHtml(selection.adds.join("; "))}`,
      `<strong>Skip:</strong> ${escapeHtml(selection.skip_when.join("; "))}`,
    ].join("<br>");

    item.append(row, detail);
    list.appendChild(item);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderPlan(plan) {
  currentPlan = plan;
  byId("preview-output").textContent = plan.preview;
  byId("progress").textContent = `${plan.progress_total} steps`;
  byId("apply").disabled = false;
  byId("confirm-row").classList.toggle("hidden", !plan.requires_confirmation);
  renderSelections(plan);
}

function renderProgress(log) {
  const list = byId("progress-log");
  list.replaceChildren();
  for (const line of log || []) {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  }
}

async function reviewPlan() {
  try {
    setBusy(true);
    setStatus("Reviewing plan...");
    const plan = await api("/api/review", {
      method: "POST",
      body: JSON.stringify(collectPayload()),
    });
    renderPlan(plan);
    setStatus(plan.status, "success");
  } catch (error) {
    currentPlan = null;
    byId("apply").disabled = true;
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function applyPlan() {
  if (!currentPlan) {
    await reviewPlan();
  }
  if (!currentPlan) {
    return;
  }
  try {
    setBusy(true);
    setStatus(`Starting ${currentPlan.action}...`);
    const payload = collectPayload({includeSelections: true});
    payload.plan_id = currentPlan.plan_id;
    payload.confirmed = byId("confirm").checked;
    const result = await api("/api/apply", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderPlan(result);
    renderProgress(result.progress_log);
    const completion = byId("completion");
    completion.textContent = result.readme_warning
      ? `${result.completion_message}\n\n${result.readme_warning}`
      : result.completion_message;
    completion.classList.remove("hidden");
    setStatus(result.status, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function setBusy(busy) {
  byId("review").disabled = busy;
  byId("apply").disabled = busy || !currentPlan;
}

async function quitInstaller() {
  try {
    await api("/api/shutdown", {method: "POST", body: "{}"});
    setStatus("Installer closed.", "success");
    window.close();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function startHeartbeat() {
  window.setInterval(() => {
    api("/api/ping", {method: "POST", body: "{}"}).catch(() => {});
  }, 30000);
}

async function boot() {
  try {
    appState = await api("/api/state");
    fillSelect(byId("operation"), appState.operation_choices, "install");
    fillSelect(byId("mode"), appState.mode_choices, "auto");
    fillSelect(byId("spec-kit-mode"), appState.spec_kit_mode_choices, "auto");
    fillSelect(byId("spec-kit-script"), appState.spec_kit_script_choices, "auto");
    fillSelect(byId("spec-kit-surface"), appState.spec_kit_command_surface_choices, "auto");
    fillSelect(byId("utility-harness-mode"), appState.utility_harness_mode_choices, "off");
    syncOperationControls();
    startHeartbeat();
    setStatus("Ready");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

for (const id of [
  "target",
  "mode",
  "force",
  "allow-dirty",
  "spec-kit-mode",
  "spec-kit-script",
  "spec-kit-surface",
  "spec-kit-version",
  "utility-harness-dependencies",
]) {
  byId(id).addEventListener("change", resetPlan);
}

byId("operation").addEventListener("change", () => {
  resetPlan();
  syncOperationControls();
});
byId("utility-harness-mode").addEventListener("change", () => {
  resetPlan();
  syncUtilityDependencyControl();
});
byId("review").addEventListener("click", () => {
  selectionsKnown = selectionsKnown && Boolean(currentPlan);
  reviewPlan();
});
byId("apply").addEventListener("click", applyPlan);
byId("quit").addEventListener("click", quitInstaller);

boot();
"""


if __name__ == "__main__":
    raise SystemExit(main())
