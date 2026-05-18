#!/usr/bin/env python3
"""Qt GUI wrapper for the Codex Enhancer installer."""

from __future__ import annotations

import argparse
import importlib.util
import queue
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.install_enhancer import (
    InstallPlan,
    apply_install_plan,
    build_overwrite_confirmation_message,
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
from scripts.install_enhancer_web_gui import build_plan_from_browser_payload


WINDOW_TITLE = "Codex Enhancer Installer"
QT_BINDING_NAMES = ("PyQt6", "PySide6")


class QtBindingError(RuntimeError):
    """Raised when no supported Qt binding can be imported."""


@dataclass(frozen=True)
class QtBinding:
    name: str
    QtCore: Any
    QtGui: Any
    QtWidgets: Any


def qt_binding_status(names: tuple[str, ...] = QT_BINDING_NAMES) -> dict[str, bool]:
    """Return whether each supported Qt binding is importable in this Python."""

    return {name: importlib.util.find_spec(name) is not None for name in names}


def import_qt_binding(preferred: tuple[str, ...] = QT_BINDING_NAMES) -> QtBinding:
    """Import the first available Qt binding."""

    errors: list[str] = []
    for name in preferred:
        try:
            if name == "PyQt6":
                from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
            elif name == "PySide6":
                from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
            else:
                raise ImportError(f"Unsupported Qt binding {name!r}.")
        except ImportError as error:
            errors.append(f"{name}: {error}")
            continue
        return QtBinding(name=name, QtCore=QtCore, QtGui=QtGui, QtWidgets=QtWidgets)

    detail = "; ".join(errors) if errors else "no supported bindings were requested"
    raise QtBindingError(f"No supported Qt binding is available ({detail}).")


def qt_dependency_help() -> str:
    return (
        "Install the optional standalone GUI dependency with "
        "`python -m pip install -e .[gui]` for PyQt6, or "
        "`python -m pip install -e .[pyside]` for PySide6."
    )


def _combo_value(combo: Any) -> str:
    value = combo.currentData()
    return str(value) if value is not None else combo.currentText()


def _clear_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child_layout is not None:
            _clear_layout(child_layout)


def run_qt_gui(binding: QtBinding) -> int:
    QtCore = binding.QtCore
    QtGui = binding.QtGui
    QtWidgets = binding.QtWidgets

    class InstallerWindow(QtWidgets.QMainWindow):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.current_plan: InstallPlan | None = None
            self.selection_checks: dict[str, Any] = {}
            self.apply_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
            self.apply_thread: threading.Thread | None = None
            self.rendering = False
            self.syncing = False

            self.setWindowTitle(WINDOW_TITLE)
            self.resize(1180, 760)
            self.setMinimumSize(880, 620)
            self._build_ui()
            self._connect_signals()
            self._sync_operation_controls()

            self.apply_timer = QtCore.QTimer(self)
            self.apply_timer.setInterval(80)
            self.apply_timer.timeout.connect(self._drain_apply_queue)

        def _build_ui(self) -> None:
            central = QtWidgets.QWidget()
            shell = QtWidgets.QVBoxLayout(central)
            shell.setContentsMargins(18, 18, 18, 18)
            shell.setSpacing(14)

            header = QtWidgets.QHBoxLayout()
            title_box = QtWidgets.QVBoxLayout()
            eyebrow = QtWidgets.QLabel("CODEX ENHANCER")
            eyebrow.setObjectName("Eyebrow")
            title = QtWidgets.QLabel("Installer")
            title.setObjectName("Title")
            title_box.addWidget(eyebrow)
            title_box.addWidget(title)
            header.addLayout(title_box, 1)

            self.status_label = QtWidgets.QLabel(f"Ready. Qt binding: {binding.name}.")
            self.status_label.setObjectName("Status")
            self.status_label.setWordWrap(True)
            header.addWidget(self.status_label, 2)
            shell.addLayout(header)

            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            splitter.addWidget(self._build_control_panel())
            splitter.addWidget(self._build_work_panel())
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([380, 760])
            shell.addWidget(splitter, 1)

            self.setCentralWidget(central)
            self.setStyleSheet(QT_STYLE)

        def _build_control_panel(self) -> Any:
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMinimumWidth(340)
            scroll.setObjectName("ControlScroll")

            panel = QtWidgets.QWidget()
            form = QtWidgets.QVBoxLayout(panel)
            form.setContentsMargins(14, 14, 14, 14)
            form.setSpacing(12)

            target_label = QtWidgets.QLabel("Target repository path")
            self.target_edit = QtWidgets.QLineEdit()
            self.target_edit.setPlaceholderText(r"D:\Projects\target-repo")
            browse_button = QtWidgets.QPushButton("Browse")
            browse_button.clicked.connect(self._browse_for_target)
            self.browse_button = browse_button

            target_row = QtWidgets.QHBoxLayout()
            target_row.addWidget(self.target_edit, 1)
            target_row.addWidget(browse_button)
            form.addWidget(target_label)
            form.addLayout(target_row)

            self.operation_combo = QtWidgets.QComboBox()
            self._fill_combo(self.operation_combo, OPERATION_CHOICES, "install")
            form.addWidget(QtWidgets.QLabel("Operation"))
            form.addWidget(self.operation_combo)

            self.mode_combo = QtWidgets.QComboBox()
            self._fill_combo(self.mode_combo, MODE_CHOICES, "auto")
            form.addWidget(QtWidgets.QLabel("Repo mode"))
            form.addWidget(self.mode_combo)

            self.force_check = QtWidgets.QCheckBox("Overwrite conflicts")
            self.allow_dirty_check = QtWidgets.QCheckBox("Allow unrelated git changes")
            form.addWidget(self.force_check)
            form.addWidget(self.allow_dirty_check)
            form.addWidget(self._separator())

            self.spec_kit_mode_combo = QtWidgets.QComboBox()
            self._fill_combo(self.spec_kit_mode_combo, SPEC_KIT_MODE_CHOICES, "auto")
            self.spec_kit_script_combo = QtWidgets.QComboBox()
            self._fill_combo(self.spec_kit_script_combo, SPEC_KIT_SCRIPT_CHOICES, "auto")
            self.spec_kit_surface_combo = QtWidgets.QComboBox()
            self._fill_combo(
                self.spec_kit_surface_combo,
                SPEC_KIT_COMMAND_SURFACE_CHOICES,
                "auto",
            )
            self.spec_kit_version_edit = QtWidgets.QLineEdit()
            self.spec_kit_version_edit.setPlaceholderText("latest")

            form.addWidget(QtWidgets.QLabel("Spec Kit"))
            form.addWidget(self.spec_kit_mode_combo)
            form.addWidget(QtWidgets.QLabel("Script flavor"))
            form.addWidget(self.spec_kit_script_combo)
            form.addWidget(QtWidgets.QLabel("Command surface"))
            form.addWidget(self.spec_kit_surface_combo)
            form.addWidget(QtWidgets.QLabel("Spec Kit ref"))
            form.addWidget(self.spec_kit_version_edit)
            form.addWidget(self._separator())

            self.utility_harness_combo = QtWidgets.QComboBox()
            self._fill_combo(self.utility_harness_combo, UTILITY_HARNESS_MODE_CHOICES, "off")
            self.utility_dependencies_check = QtWidgets.QCheckBox("Install helper dependencies")
            form.addWidget(QtWidgets.QLabel("Utility Harness"))
            form.addWidget(self.utility_harness_combo)
            form.addWidget(self.utility_dependencies_check)

            self.confirm_check = QtWidgets.QCheckBox("Confirm overwrite actions")
            self.confirm_check.setObjectName("ConfirmCheck")
            form.addWidget(self.confirm_check)

            buttons = QtWidgets.QHBoxLayout()
            self.review_button = QtWidgets.QPushButton("Review")
            self.apply_button = QtWidgets.QPushButton("Apply")
            self.apply_button.setEnabled(False)
            close_button = QtWidgets.QPushButton("Close")
            close_button.setObjectName("SecondaryButton")
            close_button.clicked.connect(self.close)
            buttons.addWidget(self.review_button)
            buttons.addWidget(self.apply_button)
            buttons.addWidget(close_button)
            form.addLayout(buttons)
            form.addStretch(1)

            scroll.setWidget(panel)
            return scroll

        def _build_work_panel(self) -> Any:
            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            splitter.addWidget(self._build_preview_panel())
            splitter.addWidget(self._build_selection_panel())
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([470, 260])
            return splitter

        def _build_preview_panel(self) -> Any:
            group = QtWidgets.QGroupBox("Preview")
            layout = QtWidgets.QVBoxLayout(group)

            self.preview = QtWidgets.QPlainTextEdit()
            self.preview.setReadOnly(True)
            self.preview.setPlainText("Enter a target path and review the plan.")
            self.preview.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
            self.preview.setFont(QtGui.QFont("Cascadia Mono", 10))
            layout.addWidget(self.preview, 1)

            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            layout.addWidget(self.progress)

            self.progress_log = QtWidgets.QPlainTextEdit()
            self.progress_log.setReadOnly(True)
            self.progress_log.setMaximumHeight(110)
            self.progress_log.setPlaceholderText("Progress appears while applying a plan.")
            layout.addWidget(self.progress_log)
            return group

        def _build_selection_panel(self) -> Any:
            group = QtWidgets.QGroupBox("Stack Packs")
            layout = QtWidgets.QVBoxLayout(group)

            header = QtWidgets.QHBoxLayout()
            self.selection_title = QtWidgets.QLabel("Guidance Packs")
            self.selection_count = QtWidgets.QLabel("0 selected")
            self.selection_count.setObjectName("Muted")
            header.addWidget(self.selection_title, 1)
            header.addWidget(self.selection_count)
            layout.addLayout(header)

            self.selection_scroll = QtWidgets.QScrollArea()
            self.selection_scroll.setWidgetResizable(True)
            self.selection_inner = QtWidgets.QWidget()
            self.selection_layout = QtWidgets.QVBoxLayout(self.selection_inner)
            self.selection_layout.setContentsMargins(8, 8, 8, 8)
            self.selection_layout.setSpacing(10)
            self.selection_scroll.setWidget(self.selection_inner)
            layout.addWidget(self.selection_scroll, 1)

            self._show_selection_placeholder("Selections appear after review.")
            return group

        def _separator(self) -> Any:
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            return line

        def _connect_signals(self) -> None:
            for combo in (
                self.operation_combo,
                self.mode_combo,
                self.spec_kit_mode_combo,
                self.spec_kit_script_combo,
                self.spec_kit_surface_combo,
                self.utility_harness_combo,
            ):
                combo.currentIndexChanged.connect(self._on_inputs_changed)
            for checkbox in (
                self.force_check,
                self.allow_dirty_check,
                self.utility_dependencies_check,
            ):
                checkbox.stateChanged.connect(self._on_inputs_changed)
            self.confirm_check.stateChanged.connect(self._refresh_apply_button)
            self.target_edit.textChanged.connect(self._on_inputs_changed)
            self.spec_kit_version_edit.textChanged.connect(self._on_inputs_changed)
            self.review_button.clicked.connect(self._review_plan)
            self.apply_button.clicked.connect(self._apply_plan)

        def _fill_combo(
            self,
            combo: Any,
            choices: tuple[tuple[str, str], ...],
            default: str,
        ) -> None:
            current = _combo_value(combo) if combo.count() else default
            combo.blockSignals(True)
            combo.clear()
            for label, value in choices:
                combo.addItem(label, value)
            index = combo.findData(current)
            if index < 0:
                index = combo.findData(default)
            combo.setCurrentIndex(max(index, 0))
            combo.blockSignals(False)

        def _sync_operation_controls(self) -> None:
            self.syncing = True
            operation = _combo_value(self.operation_combo)
            is_refresh = operation == "refresh-generated"
            is_manage = operation in {"manage-packs", "manage-workflows"}
            is_upgrade = operation == "upgrade-enhancer"

            self.mode_combo.setEnabled(not (is_refresh or is_manage or is_upgrade))
            self.force_check.setEnabled(not (is_refresh or is_manage or is_upgrade))
            spec_enabled = not (is_refresh or is_manage)
            for widget in (
                self.spec_kit_mode_combo,
                self.spec_kit_script_combo,
                self.spec_kit_surface_combo,
                self.spec_kit_version_edit,
            ):
                widget.setEnabled(spec_enabled)

            choices = (
                UTILITY_HARNESS_UPGRADE_MODE_CHOICES
                if is_upgrade
                else UTILITY_HARNESS_MODE_CHOICES
            )
            default = choices[0][1]
            self._fill_combo(self.utility_harness_combo, choices, default)
            utility_enabled = not (is_refresh or is_manage)
            self.utility_harness_combo.setEnabled(utility_enabled)
            self.utility_dependencies_check.setEnabled(
                utility_enabled and _combo_value(self.utility_harness_combo) == "install"
            )
            if not self.utility_dependencies_check.isEnabled():
                self.utility_dependencies_check.setChecked(False)
            self.syncing = False

        def _on_inputs_changed(self, *_args: object) -> None:
            if self.syncing or self.rendering:
                return
            self._sync_operation_controls()
            self.current_plan = None
            self.confirm_check.setChecked(False)
            self.apply_button.setEnabled(False)
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress_log.clear()
            self.preview.setPlainText("Inputs changed. Review the plan again.")
            self._show_selection_placeholder("Selections appear after review.")
            self._set_status("Inputs changed. Review again before applying.")

        def _collect_payload(self, *, include_selections: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "target": self.target_edit.text().strip(),
                "operation": _combo_value(self.operation_combo),
                "mode": _combo_value(self.mode_combo),
                "force": self.force_check.isChecked(),
                "allow_dirty": self.allow_dirty_check.isChecked(),
                "spec_kit_mode": _combo_value(self.spec_kit_mode_combo),
                "spec_kit_script": _combo_value(self.spec_kit_script_combo),
                "spec_kit_command_surface": _combo_value(self.spec_kit_surface_combo),
                "spec_kit_version": self.spec_kit_version_edit.text().strip(),
                "utility_harness_mode": _combo_value(self.utility_harness_combo),
                "utility_harness_dependencies": self.utility_dependencies_check.isChecked(),
            }
            if include_selections:
                payload["selected_packs"] = [
                    name
                    for name, checkbox in self.selection_checks.items()
                    if checkbox.isChecked()
                ]
            return payload

        def _browse_for_target(self) -> None:
            chosen = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Choose the repository folder for Codex Enhancer",
                self.target_edit.text().strip() or str(Path.cwd()),
            )
            if chosen:
                self.target_edit.setText(chosen)

        def _review_plan(self) -> None:
            if not self.target_edit.text().strip():
                QtWidgets.QMessageBox.critical(
                    self,
                    WINDOW_TITLE,
                    "Choose or type a repository folder first.",
                )
                return
            try:
                plan = build_plan_from_browser_payload(
                    self._collect_payload(include_selections=bool(self.selection_checks))
                )
            except ValueError as error:
                self.current_plan = None
                self.preview.setPlainText("No valid plan is available yet.")
                self._set_status(str(error), error=True)
                QtWidgets.QMessageBox.critical(self, WINDOW_TITLE, str(error))
                self._refresh_apply_button()
                return
            self._render_plan(plan)

        def _render_plan(self, plan: InstallPlan) -> None:
            self.rendering = True
            self.current_plan = plan
            self.preview.setPlainText(build_plan_preview(plan))
            self.progress.setRange(0, max(progress_total(plan), 1))
            self.progress.setValue(0)
            self.progress_log.clear()
            self.confirm_check.setVisible(requires_confirmation(plan))
            self.confirm_check.setChecked(False)
            self._render_selections(plan)
            self._set_status("Plan ready.")
            self.rendering = False
            self._refresh_apply_button()

        def _render_selections(self, plan: InstallPlan) -> None:
            _clear_layout(self.selection_layout)
            self.selection_checks = {}
            selections = (
                plan.workflow_selections
                if plan.operation == "manage-workflows"
                else plan.pack_selections
            )
            selected_count = sum(1 for selection in selections if selection.selected)
            self.selection_title.setText(
                "Workflow Packs" if plan.operation == "manage-workflows" else "Stack Packs"
            )
            self.selection_count.setText(f"{selected_count} selected")

            if not selections:
                self._show_selection_placeholder("No packs are available for this operation.")
                return

            interactive = plan.operation != "refresh-generated"
            for selection in selections:
                card = QtWidgets.QFrame()
                card.setObjectName("SelectionCard")
                card_layout = QtWidgets.QVBoxLayout(card)
                card_layout.setContentsMargins(10, 10, 10, 10)
                card_layout.setSpacing(6)

                checkbox = QtWidgets.QCheckBox(
                    f"{selection.pack.label} ({selection.pack.name})"
                )
                checkbox.setChecked(selection.selected)
                checkbox.setEnabled(interactive)
                checkbox.stateChanged.connect(self._on_selection_changed)
                self.selection_checks[selection.pack.name] = checkbox
                card_layout.addWidget(checkbox)

                reason = "; ".join(selection.reasons) or "manual review"
                details = QtWidgets.QLabel(
                    "\n".join(
                        [
                            f"{'Recommended' if selection.recommended else 'Optional'}: {reason}",
                            f"What it does: {selection.pack.description}",
                            f"Enable when: {'; '.join(selection.pack.guidance.use_when)}",
                            f"Adds: {'; '.join(selection.pack.guidance.adds)}",
                            f"Skip when: {'; '.join(selection.pack.guidance.skip_when)}",
                        ]
                    )
                )
                details.setWordWrap(True)
                details.setObjectName("SelectionDetails")
                details.setTextInteractionFlags(
                    QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
                )
                card_layout.addWidget(details)
                self.selection_layout.addWidget(card)
            self.selection_layout.addStretch(1)

        def _show_selection_placeholder(self, message: str) -> None:
            _clear_layout(self.selection_layout)
            self.selection_checks = {}
            label = QtWidgets.QLabel(message)
            label.setWordWrap(True)
            label.setObjectName("Muted")
            self.selection_layout.addWidget(label)
            self.selection_layout.addStretch(1)
            self.selection_count.setText("0 selected")

        def _on_selection_changed(self, *_args: object) -> None:
            if self.rendering or self.current_plan is None:
                return
            try:
                plan = build_plan_from_browser_payload(
                    self._collect_payload(include_selections=True)
                )
            except ValueError as error:
                self._set_status(str(error), error=True)
                return
            self._render_plan(plan)

        def _refresh_apply_button(self, *_args: object) -> None:
            plan = self.current_plan
            if plan is None or self._is_busy():
                self.apply_button.setEnabled(False)
                return
            self.apply_button.setEnabled(
                (not requires_confirmation(plan)) or self.confirm_check.isChecked()
            )

        def _apply_plan(self) -> None:
            plan = self.current_plan
            if plan is None:
                self._set_status("Review the current plan before applying.", error=True)
                return
            if requires_confirmation(plan) and not self.confirm_check.isChecked():
                QtWidgets.QMessageBox.warning(
                    self,
                    WINDOW_TITLE,
                    build_overwrite_confirmation_message(plan),
                )
                return

            self._set_busy(True)
            total = max(progress_total(plan), 1)
            self.progress.setRange(0, total)
            self.progress.setValue(0)
            self.progress_log.clear()
            self._set_status(f"Starting {action_verb(plan)}...")
            allow_dirty = self.allow_dirty_check.isChecked()
            self.apply_queue = queue.Queue()
            self.apply_thread = threading.Thread(
                target=self._apply_worker,
                args=(plan, allow_dirty),
                daemon=True,
            )
            self.apply_thread.start()
            self.apply_timer.start()

        def _apply_worker(self, plan: InstallPlan, allow_dirty: bool) -> None:
            progress_log: list[str] = []

            def on_progress(current: int, total: int, message: str) -> None:
                progress_log.append(f"{current}/{total} {message}")
                self.apply_queue.put(("progress", (current, total, message)))

            try:
                apply_install_plan(
                    plan,
                    progress_callback=on_progress,
                    allow_dirty=allow_dirty,
                )
            except Exception as error:  # pragma: no cover - GUI recovery path
                self.apply_queue.put(("error", error))
                return
            self.apply_queue.put(("done", progress_log))

        def _drain_apply_queue(self) -> None:
            while True:
                try:
                    event, payload = self.apply_queue.get_nowait()
                except queue.Empty:
                    break
                if event == "progress":
                    current, total, message = payload
                    self.progress.setRange(0, max(total, 1))
                    self.progress.setValue(current)
                    self.progress_log.appendPlainText(f"{current}/{total} {message}")
                    self._set_status(message)
                elif event == "error":
                    self.apply_timer.stop()
                    self._set_busy(False)
                    action = action_verb(self.current_plan).capitalize() if self.current_plan else "Apply"
                    self._set_status(f"{action} failed: {payload}", error=True)
                    QtWidgets.QMessageBox.critical(
                        self,
                        WINDOW_TITLE,
                        f"{action} failed:\n\n{payload}",
                    )
                elif event == "done":
                    self.apply_timer.stop()
                    self._set_busy(False)
                    plan = self.current_plan
                    if plan is None:
                        return
                    self.preview.setPlainText(build_plan_preview(plan))
                    self.progress.setValue(self.progress.maximum())
                    self._set_status(f"{action_verb(plan).capitalize()} complete.")
                    QtWidgets.QMessageBox.information(
                        self,
                        WINDOW_TITLE,
                        build_completion_message(plan),
                    )
                    try:
                        open_product_readme()
                    except OSError as error:  # pragma: no cover - platform opener failure
                        QtWidgets.QMessageBox.warning(
                            self,
                            WINDOW_TITLE,
                            "The install finished, but the README could not be opened automatically."
                            f"\n\n{error}",
                        )
                    break

        def _set_busy(self, busy: bool) -> None:
            if not busy:
                self._sync_operation_controls()
            for widget in (
                self.review_button,
                self.browse_button,
                self.target_edit,
                self.operation_combo,
                self.mode_combo,
                self.force_check,
                self.allow_dirty_check,
                self.spec_kit_mode_combo,
                self.spec_kit_script_combo,
                self.spec_kit_surface_combo,
                self.spec_kit_version_edit,
                self.utility_harness_combo,
                self.utility_dependencies_check,
                self.confirm_check,
            ):
                widget.setEnabled(not busy)
            if busy:
                self.apply_button.setEnabled(False)
            else:
                self._refresh_apply_button()

        def _is_busy(self) -> bool:
            return self.apply_thread is not None and self.apply_thread.is_alive()

        def _set_status(self, message: str, *, error: bool = False) -> None:
            self.status_label.setText(message)
            self.status_label.setProperty("error", error)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)

        def closeEvent(self, event: Any) -> None:
            if self._is_busy():
                answer = QtWidgets.QMessageBox.question(
                    self,
                    WINDOW_TITLE,
                    "An install action is still running. Close the installer anyway?",
                )
                if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            event.accept()

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName(WINDOW_TITLE)
    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    window = InstallerWindow()
    window.show()
    return int(app.exec())


QT_STYLE = """
QMainWindow {
    background: #f5f2ea;
}
QLabel#Eyebrow {
    color: #0f766e;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0;
}
QLabel#Title {
    color: #18211f;
    font-size: 34px;
    font-weight: 800;
}
QLabel#Status {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #fffdf8;
    color: #4f5d59;
    padding: 10px 12px;
}
QLabel#Status[error="true"] {
    color: #9f1239;
    border-color: #d89aa9;
}
QGroupBox {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    margin-top: 12px;
    background: #fffdf8;
    color: #18211f;
    font-weight: 800;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QScrollArea#ControlScroll,
QScrollArea {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #fffdf8;
}
QLineEdit,
QComboBox {
    min-height: 32px;
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #ffffff;
    color: #18211f;
    padding: 6px 9px;
}
QCheckBox {
    color: #38433f;
    spacing: 8px;
}
QPushButton {
    min-height: 34px;
    border: 0;
    border-radius: 8px;
    background: #0f766e;
    color: #ffffff;
    font-weight: 800;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #115e59;
}
QPushButton:disabled {
    background: #9fb5b1;
}
QPushButton#SecondaryButton {
    border: 1px solid #d8d0c1;
    background: #ffffff;
    color: #18211f;
}
QCheckBox#ConfirmCheck {
    border: 1px solid #c89345;
    border-radius: 8px;
    background: #f8ead2;
    padding: 8px;
}
QPlainTextEdit {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #171f1d;
    color: #edf7f2;
    padding: 8px;
}
QProgressBar {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #fffdf8;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: #0f766e;
}
QFrame#SelectionCard {
    border: 1px solid #d8d0c1;
    border-radius: 8px;
    background: #ffffff;
}
QLabel#SelectionDetails,
QLabel#Muted {
    color: #64706d;
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_enhancer_qt_gui.py",
        description="Open the Codex Enhancer Qt GUI installer.",
    )
    parser.add_argument(
        "--no-browser-fallback",
        action="store_true",
        help="return an error instead of opening the browser GUI when Qt is unavailable",
    )
    parser.add_argument(
        "--binding",
        choices=QT_BINDING_NAMES,
        help="prefer a specific Qt binding when both are installed",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    preferred = (args.binding,) if args.binding else QT_BINDING_NAMES
    try:
        binding = import_qt_binding(preferred)
    except QtBindingError as error:
        if args.no_browser_fallback:
            print(f"{error}\n\n{qt_dependency_help()}", file=sys.stderr)
            return 1
        print(
            f"Qt GUI dependency not available; opening the browser GUI instead.\n{qt_dependency_help()}",
            file=sys.stderr,
        )
        from scripts.install_enhancer_web_gui import main as browser_main

        return browser_main([])

    return run_qt_gui(binding)


if __name__ == "__main__":
    raise SystemExit(main())
