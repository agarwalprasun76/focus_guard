"""Shown once after first-run wizard exits and full services + tray have started."""

from __future__ import annotations

import webbrowser

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTextBrowser,
    QSizePolicy,
)

from focus_guard.gui.setup_health_checks import (
    admin_dashboard_http_url,
    evaluate_setup_health,
)


class PostFirstRunSetupDialog(QDialog):
    """Open dashboard / run probes after the full runtime stack is up."""

    def __init__(
        self,
        parent=None,
        tray_icon=None,
        *,
        width: int = 520,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.MSWindowsFixedSizeDialogHint
        )
        self.setModal(True)
        self.setWindowTitle("Finish setup")

        dash_url = admin_dashboard_http_url()

        outer = QVBoxLayout(self)

        intro = QLabel(
            "Focus Guard is running in your system tray.<br>"
            "Now that services are starting here, verify the guardian dashboard "
            "and browser extension.<br>"
            f"<small>Dashboard: <code>{dash_url}</code></small>"
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        outer.addWidget(intro)

        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._browser.setMinimumHeight(120)
        self._browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        btns = QHBoxLayout()

        dash_btn = QPushButton("Open Guardian Dashboard")
        dash_btn.clicked.connect(self._open_dashboard)
        dash_btn.setToolTip(f"Open {dash_url}")
        btns.addWidget(dash_btn)

        check_btn = QPushButton("Run connection check")
        check_btn.clicked.connect(self._run_check)
        check_btn.setToolTip("Ping tab server, admin gateway, and extension handshake.")
        btns.addWidget(check_btn)

        btns.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)

        outer.addWidget(self._browser)
        outer.addLayout(btns)

        if tray_icon and not tray_icon.isNull():
            try:
                self.setWindowIcon(tray_icon.icon())
            except AttributeError:
                pass

        self.resize(width, 360)
        self._run_check(initial=True)

    def _open_dashboard(self) -> None:
        url = admin_dashboard_http_url()
        try:
            webbrowser.open(url)
        except Exception:
            self._browser.setHtml(
                f"<span style=\"color:red\">Unable to launch the default browser. "
                f"Paste this URL manually:</span><br><code>{url}</code>"
            )

    def _run_check(self, initial: bool = False) -> None:
        """Post-start probes; wizard checkbox semantics omitted (avoid false negatives)."""

        parts: list[str] = []
        if initial:
            parts.append(
                "<p>Open <b>Guardian Dashboard</b> once the checklist below reports healthy endpoints.</p>"
            )
        try:
            res = evaluate_setup_health(
                extension_install_acknowledged=None,
                admin_password_enabled=None,
            )
            parts.append(res.html_summary)
            parts.append(
                '<p style="margin-top:8px; color:#666; font-size:11px;">'
                "Still waiting on endpoints? Focus Guard finishes loading in the tray first—give it a "
                'few seconds, then click <b>Run connection check</b> again.</p>'
            )
        except Exception as exc:
            parts = [
                '<p style="color:red">Unexpected error running checks.</p>'
                f"<p><code>{exc}</code></p>",
            ]

        self._browser.setHtml("".join(parts))
