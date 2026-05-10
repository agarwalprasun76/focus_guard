"""
Focus Guard — First-Run Setup Wizard (PyQt5).

Shown on first launch when no deployment_config.json exists.
Walks the user through: Welcome → Email → Extension → Done.
Saves a DeploymentConfig at the end.
"""

import logging
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import (
    QWizard,
    QWizardPage,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QMessageBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QProgressBar,
    QTabBar,
    QWidget,
    QDialog,
    QDialogButtonBox,
)

from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url
from focus_guard.core.tab_server_endpoint import resolve_tab_server_endpoint
from focus_guard.core.extension_constants import (
    CHROME_EXTENSION_ID,
    CHROME_STORE_URL,
    EDGE_EXTENSION_ID,
    EDGE_STORE_URL,
)
from focus_guard.core.win_store_browser import (
    open_google_chrome_url,
    open_microsoft_edge_url,
)
from focus_guard.gui.setup_health_checks import admin_dashboard_http_url

logger = logging.getLogger(__name__)

# Gmail SMTP help (opening in the user's browser is clearer than pasted URLs alone)
_GMAIL_APP_PASSWORDS_URL = "https://myaccount.google.com/apppasswords"
_GMAIL_2STEP_HELP_URL = "https://support.google.com/accounts/answer/185839"


# ---------------------------------------------------------------------------
# Helper: section header label
# ---------------------------------------------------------------------------

def _heading(text: str, size: int = 16) -> QLabel:
    lbl = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    lbl.setFont(font)
    return lbl


def _body(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


# ═══════════════════════════════════════════════════════════════════════════
# Page 1: Welcome
# ═══════════════════════════════════════════════════════════════════════════

class WelcomePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome to Focus Guard")
        self.setSubTitle("Let's get you set up in a few quick steps.")

        layout = QVBoxLayout()

        intro = _body(
            "Focus Guard is an AI-powered productivity tool that helps manage "
            "screen time and reduce distractions — perfect for students, remote workers, "
            "or anyone who wants to stay focused."
        )
        layout.addWidget(intro)

        layout.addWidget(_body(
            "How this install works: you already started Focus Guard from the main app entry point. "
            "This wizard collects your settings first (no background services yet). "
            "When you click <b>Start Focus Guard</b> on the last page, the tray and services "
            "come up next; shortly after that, a short <i>Finish setup</i> window helps you "
            "open the guardian dashboard and verify connections. "
            "Later, use Settings from the tray—not a separate setup launcher—to change choices."
        ))
        layout.addWidget(_separator())

        # Features section
        features_group = QGroupBox("What Focus Guard Does")
        features_layout = QVBoxLayout()

        features = [
            ("🔍 Smart Classification", "Automatically categorizes websites as educational, entertainment, social media, etc."),
            ("⏱️ Time Budgets", "Set daily limits for distracting content — when time runs out, sites are blocked."),
            ("🚫 Distraction Blocking", "Blocks access to distracting sites and shows a helpful reminder page."),
            ("📊 Activity Reports", "Sends email reports to parents/guardians with usage summaries."),
            ("🔒 Bypass Protection", "Prevents easy workarounds like incognito mode or extension removal."),
        ]

        for title, desc in features:
            row = QHBoxLayout()
            title_lbl = QLabel(f"<b>{title}</b>")
            title_lbl.setMinimumWidth(180)
            row.addWidget(title_lbl)
            row.addWidget(_body(desc), 1)
            features_layout.addLayout(row)

        features_group.setLayout(features_layout)
        layout.addWidget(features_group)

        layout.addStretch()

        # Setup steps preview
        steps = _body(
            "This wizard will guide you through:\n"
            "  1. Email reports setup (optional)\n"
            "  2. Browser extension installation\n"
            "  3. Time limits configuration\n"
            "  4. Personalization options\n"
            "  5. Domain management\n"
            "  6. Admin password setup (recommended)\n"
        )
        steps.setStyleSheet("color: #555;")
        layout.addWidget(steps)

        footer = _body("You can change any of these settings later from the system tray menu.")
        footer.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(footer)

        self.setLayout(layout)


# ═══════════════════════════════════════════════════════════════════════════
# Page 2: Email Configuration
# ═══════════════════════════════════════════════════════════════════════════

class EmailPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Email Reports")
        self.setSubTitle("Configure email to receive activity reports (optional).")

        layout = QVBoxLayout()

        # --- Explanation ---
        explanation = _body(
            "Focus Guard can send activity reports to a parent, guardian, or yourself. "
            "Reports include:\n"
            "  • Time spent on educational vs. distracting sites\n"
            "  • Override requests and their outcomes\n"
            "  • Blocked site attempts\n"
            "  • Daily focus score and trends\n"
        )
        layout.addWidget(explanation)

        layout.addWidget(_separator())

        self.enable_email = QCheckBox("Enable email reports")
        self.enable_email.setChecked(True)
        self.enable_email.toggled.connect(self._toggle_fields)
        layout.addWidget(self.enable_email)

        # --- SMTP group ---
        self.smtp_group = QGroupBox("SMTP Settings (Your Email Provider)")
        smtp_layout = QVBoxLayout()

        smtp_desc = _body(
            "These credentials are only for Focus Guard to log into your outgoing mail server. "
            "Use the email address that will appear as sender under “Your Email”. "
            "For Gmail, your normal Gmail password usually does not work here—use Google’s separate "
            "App password shown in the steps below."
        )
        smtp_desc.setStyleSheet("color: #555; font-size: 11px;")
        smtp_layout.addWidget(smtp_desc)

        gmail_group = QGroupBox("Gmail (@gmail.com): get an App password")
        gmail_layout = QVBoxLayout()

        gmail_steps_text = QLabel(
            "<p><b>If you send reports from Gmail (@gmail.com),</b> do this once in your browser:</p>"
            "<p>1.&nbsp;&nbsp;Sign in to Google as the <b>same inbox</b> you will type under "
            "&quot;Your Email&quot; (for example your monitoring Gmail account).</p>"
            "<p>2.&nbsp;&nbsp;Enable <b>2-Step Verification</b>. Until this is on, Google will "
            "not offer App passwords.</p>"
            "<p>3.&nbsp;&nbsp;Open <b>App passwords</b>, create one named Focus Guard, and copy the "
            "<b>16 characters</b> (often shown as four blocks).</p>"
            "<p>4.&nbsp;&nbsp;Paste them into “Gmail App password” below. That is "
            "<b>not</b> the password you normally use to sign in to gmail.com.</p>"
            "<p style=\"color:#666;font-size:11px;\"><i>For Outlook, Yahoo, or another provider, "
            "use their SMTP or “app password” instructions instead—this block is Gmail-only.</i></p>"
        )
        gmail_steps_text.setWordWrap(True)
        gmail_steps_text.setTextFormat(Qt.RichText)
        gmail_layout.addWidget(gmail_steps_text)

        gmail_btn_row = QHBoxLayout()
        open_pw_btn = QPushButton("Open Google “App passwords”")
        open_pw_btn.clicked.connect(
            lambda: EmailPage._open_url_in_browser(_GMAIL_APP_PASSWORDS_URL)
        )
        open_pw_btn.setToolTip("Opens Google Account → App passwords in your browser.")
        gmail_btn_row.addWidget(open_pw_btn)

        open_2sv_btn = QPushButton("How to turn on 2-Step Verification")
        open_2sv_btn.clicked.connect(
            lambda: EmailPage._open_url_in_browser(_GMAIL_2STEP_HELP_URL)
        )
        open_2sv_btn.setToolTip("Google Help: enable 2-Step Verification.")
        gmail_btn_row.addWidget(open_2sv_btn)
        gmail_btn_row.addStretch()
        gmail_layout.addLayout(gmail_btn_row)

        gmail_group.setLayout(gmail_layout)
        smtp_layout.addWidget(gmail_group)

        form = QFormLayout()

        self.smtp_server = QLineEdit("smtp.gmail.com")
        self.smtp_server.setToolTip("The outgoing mail server (e.g., smtp.gmail.com for Gmail)")
        form.addRow("SMTP Server:", self.smtp_server)

        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_port.setToolTip("Usually 587 for TLS or 465 for SSL")
        form.addRow("SMTP Port:", self.smtp_port)

        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("e.g. monitoring-account@gmail.com")
        self.smtp_user.setToolTip(
            "The From / login address for SMTP (often a dedicated Gmail like focusguardapp@gmail.com)."
        )
        form.addRow("Your Email:", self.smtp_user)

        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_pass.setPlaceholderText("Paste Google’s 16-character App password here")
        self.smtp_pass.setToolTip(
            "Gmail: after 2-Step Verification is on, create an App password and paste those 16 characters. "
            "Other providers: their SMTP password or app password."
        )
        form.addRow("Gmail App password:", self.smtp_pass)

        smtp_layout.addLayout(form)
        self.smtp_group.setLayout(smtp_layout)
        layout.addWidget(self.smtp_group)

        # --- Recipients ---
        self.recip_group = QGroupBox("Report Recipients")
        recip_layout = QVBoxLayout()

        recip_desc = _body(
            "Who should receive the activity reports? This is typically a parent or guardian. "
            "Separate multiple addresses with commas."
        )
        recip_layout.addWidget(recip_desc)

        self.recipients = QLineEdit()
        self.recipients.setPlaceholderText("parent@example.com, guardian@example.com")
        self.recipients.setToolTip("Email addresses that will receive activity reports")
        recip_layout.addWidget(self.recipients)

        self.recip_group.setLayout(recip_layout)
        layout.addWidget(self.recip_group)

        # --- Frequency ---
        freq_group = QGroupBox("Report Frequency")
        freq_layout = QVBoxLayout()
        freq_desc = _body("How often should reports be sent?")
        freq_layout.addWidget(freq_desc)

        freq_row = QHBoxLayout()
        self.frequency = QComboBox()
        self.frequency.addItems(["Every 5 minutes (testing)", "Hourly", "Every 2 hours", "Every 4 hours", "Daily"])
        self.frequency.setToolTip("More frequent reports help catch issues early")
        freq_row.addWidget(self.frequency)
        freq_row.addStretch()
        freq_layout.addLayout(freq_row)
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)

        layout.addStretch()

        hint = _body(
            "Tip: Uncheck Enable email reports to configure SMTP later. "
            "You can reopen settings from the tray when you have the Gmail App password ready."
        )
        hint.setStyleSheet("color: #0066cc; background-color: #e6f2ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def _toggle_fields(self, enabled: bool):
        self.smtp_group.setEnabled(enabled)
        self.recip_group.setEnabled(enabled)
        self.frequency.setEnabled(enabled)

    @staticmethod
    def _open_url_in_browser(url: str) -> None:
        webbrowser.open(url)


# ═══════════════════════════════════════════════════════════════════════════
# Page 3: Browser Extension
# ═══════════════════════════════════════════════════════════════════════════

class ExtensionPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        _, tab_server_port = resolve_tab_server_endpoint()
        self.setTitle("Browser Extension")
        self.setSubTitle("Install the browser extension to enable real-time website blocking.")

        layout = QVBoxLayout()

        layout.addWidget(_body(
            "The browser extension enables:\n"
            "  • Real-time tab monitoring and classification\n"
            "  • Blocking distracting websites\n"
            "  • Time-budget enforcement\n"
            "  • Override requests with time limits\n\n"
            "Click a button below to install from the store:"
        ))

        # --- Edge button ---
        btn_layout = QHBoxLayout()

        edge_btn = QPushButton("  Install for Microsoft Edge")
        edge_btn.setMinimumHeight(40)
        edge_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )
        edge_btn.clicked.connect(lambda: self._open_edge_storefront())
        btn_layout.addWidget(edge_btn)

        chrome_btn = QPushButton("  Install for Chrome")
        chrome_btn.setMinimumHeight(40)
        chrome_btn.setStyleSheet(
            "QPushButton { background-color: #4285F4; color: white; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #3367D6; }"
        )
        chrome_btn.clicked.connect(lambda: self._open_chrome_storefront())
        btn_layout.addWidget(chrome_btn)

        layout.addLayout(btn_layout)

        layout.addWidget(_separator())

        layout.addWidget(_body(
            "After installing, the extension will automatically connect to "
            f"Focus Guard's local server (port {tab_server_port}). No extra configuration needed."
        ))

        layout.addWidget(_body(
            "Canonical extension IDs:\n"
            f"  • Edge: {EDGE_EXTENSION_ID}\n"
            f"  • Chrome: {CHROME_EXTENSION_ID}"
        ))

        self.extension_installed_cb = QCheckBox(
            "I installed at least one Focus Guard browser extension from the store."
        )
        self.extension_installed_cb.setToolTip(
            "Required for full blocking behavior and live tab visibility."
        )
        layout.addWidget(self.extension_installed_cb)

        layout.addStretch()

        note = _body(
            "Both the Edge and Chrome extensions are live on their respective stores."
        )
        note.setStyleSheet("color: #666;")
        layout.addWidget(note)

        self.setLayout(layout)

    @staticmethod
    def _open_edge_storefront() -> None:
        if not (
            sys.platform == "win32"
            and open_microsoft_edge_url(EDGE_STORE_URL)
        ):
            webbrowser.open(EDGE_STORE_URL)

    @staticmethod
    def _open_chrome_storefront() -> None:
        if not (
            sys.platform == "win32"
            and open_google_chrome_url(CHROME_STORE_URL)
        ):
            webbrowser.open(CHROME_STORE_URL)


# ═══════════════════════════════════════════════════════════════════════════
# Page 4: Time Limits / Budget Settings
# ═══════════════════════════════════════════════════════════════════════════

class TimeLimitsPage(QWizardPage):
    """Configure time budgets for different content categories."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Time Limits")
        self.setSubTitle("Set daily time budgets for different types of content.")

        layout = QVBoxLayout()

        # --- Explanation ---
        explanation = _body(
            "Focus Guard tracks time spent on different types of websites and enforces "
            "daily limits. When a limit is reached, the site is blocked until the next day.\n"
        )
        layout.addWidget(explanation)

        layout.addWidget(_separator())

        # --- Quick presets ---
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QVBoxLayout()
        preset_desc = _body("Choose a preset to get started quickly, or customize below.")
        preset_layout.addWidget(preset_desc)

        preset_row = QHBoxLayout()
        self._preset_strict = QPushButton("Strict (30 min)")
        self._preset_strict.setToolTip("30 min total: 15 ent / 10 social / 5 gaming, 2 overrides")
        self._preset_strict.clicked.connect(lambda: self._apply_preset(30, 15, 10, 5, 2, 3))
        preset_row.addWidget(self._preset_strict)

        self._preset_moderate = QPushButton("Moderate (45 min)")
        self._preset_moderate.setToolTip("45 min total: 30 ent / 20 social / 15 gaming, 3 overrides")
        self._preset_moderate.clicked.connect(lambda: self._apply_preset(45, 30, 20, 15, 3, 5))
        preset_row.addWidget(self._preset_moderate)

        self._preset_relaxed = QPushButton("Relaxed (90 min)")
        self._preset_relaxed.setToolTip("90 min total: 60 ent / 45 social / 30 gaming, 5 overrides")
        self._preset_relaxed.clicked.connect(lambda: self._apply_preset(90, 60, 45, 30, 5, 10))
        preset_row.addWidget(self._preset_relaxed)

        preset_layout.addLayout(preset_row)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # --- Master distraction budget ---
        master_group = QGroupBox("Master Distraction Budget")
        master_layout = QVBoxLayout()
        master_desc = _body(
            "Total daily time allowed across ALL distracting categories combined. "
            "This is the main limit that controls overall screen time."
        )
        master_layout.addWidget(master_desc)

        master_row = QHBoxLayout()
        master_row.addWidget(QLabel("Total distraction time per day:"))
        self.master_budget = QSpinBox()
        self.master_budget.setRange(5, 480)
        self.master_budget.setValue(45)
        self.master_budget.setSuffix(" minutes")
        self.master_budget.setToolTip("Total time allowed for entertainment, gaming, social media combined")
        master_row.addWidget(self.master_budget)
        master_row.addStretch()
        master_layout.addLayout(master_row)
        master_group.setLayout(master_layout)
        layout.addWidget(master_group)

        # --- Per-category budgets ---
        category_group = QGroupBox("Per-Category Limits")
        cat_layout = QVBoxLayout()
        cat_desc = _body(
            "Fine-tune limits for specific categories. These limits are within the master budget."
        )
        cat_layout.addWidget(cat_desc)

        cat_form = QFormLayout()

        self.entertainment_budget = QSpinBox()
        self.entertainment_budget.setRange(0, 240)
        self.entertainment_budget.setValue(30)
        self.entertainment_budget.setSuffix(" min")
        self.entertainment_budget.setToolTip("YouTube, Netflix, streaming sites")
        cat_form.addRow("Entertainment (YouTube, Netflix):", self.entertainment_budget)

        self.social_media_budget = QSpinBox()
        self.social_media_budget.setRange(0, 240)
        self.social_media_budget.setValue(20)
        self.social_media_budget.setSuffix(" min")
        self.social_media_budget.setToolTip("Facebook, Twitter, Instagram, Reddit, TikTok")
        cat_form.addRow("Social Media:", self.social_media_budget)

        self.gaming_budget = QSpinBox()
        self.gaming_budget.setRange(0, 240)
        self.gaming_budget.setValue(15)
        self.gaming_budget.setSuffix(" min")
        self.gaming_budget.setToolTip("Gaming sites like Steam, Roblox, Twitch")
        cat_form.addRow("Gaming:", self.gaming_budget)

        cat_layout.addLayout(cat_form)
        category_group.setLayout(cat_layout)
        layout.addWidget(category_group)

        # --- Override settings ---
        override_group = QGroupBox("Override Settings")
        override_layout = QVBoxLayout()
        override_desc = _body(
            "Overrides allow temporary access to blocked sites. Use sparingly!"
        )
        override_layout.addWidget(override_desc)

        override_form = QFormLayout()

        self.max_overrides = QSpinBox()
        self.max_overrides.setRange(0, 20)
        self.max_overrides.setValue(3)
        self.max_overrides.setToolTip("Number of override requests allowed per day")
        override_form.addRow("Max overrides per day:", self.max_overrides)

        self.override_duration = QSpinBox()
        self.override_duration.setRange(1, 60)
        self.override_duration.setValue(5)
        self.override_duration.setSuffix(" min")
        self.override_duration.setToolTip("How long each override lasts")
        override_form.addRow("Override duration:", self.override_duration)

        override_layout.addLayout(override_form)
        override_group.setLayout(override_layout)
        layout.addWidget(override_group)

        layout.addStretch()

        hint = _body(
            "💡 Tip: Start with stricter limits and adjust based on behavior. "
            "You can always change these later from Settings."
        )
        hint.setStyleSheet("color: #0066cc; background-color: #e6f2ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def _apply_preset(self, master, ent, social, gaming, overrides, override_dur):
        """Apply a time-limit preset to all spinboxes."""
        self.master_budget.setValue(master)
        self.entertainment_budget.setValue(ent)
        self.social_media_budget.setValue(social)
        self.gaming_budget.setValue(gaming)
        self.max_overrides.setValue(overrides)
        self.override_duration.setValue(override_dur)


# ═══════════════════════════════════════════════════════════════════════════
# Page 5: Personalization (Blocking Page)
# ═══════════════════════════════════════════════════════════════════════════

class PersonalizationPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Personalize Your Experience")
        self.setSubTitle("Customize what appears on the blocking page when a distraction is caught.")

        layout = QVBoxLayout()

        # --- Display name ---
        name_group = QGroupBox("Your Name")
        name_layout = QVBoxLayout()
        name_layout.addWidget(_body(
            "This name will appear in greetings on the blocking page."
        ))
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("e.g. Prasun")
        name_layout.addWidget(self.display_name)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        # --- Tone ---
        tone_layout = QHBoxLayout()
        tone_layout.addWidget(QLabel("Blocking page tone:"))
        self.tone = QComboBox()
        self.tone.addItems(["Encouraging", "Firm", "Playful"])
        self.tone.setCurrentIndex(0)
        tone_layout.addWidget(self.tone)
        tone_layout.addStretch()
        layout.addLayout(tone_layout)

        layout.addWidget(_separator())

        # --- Feature toggles ---
        layout.addWidget(_body("Choose what to show on the blocking page:"))

        self.show_streak = QCheckBox("Show focus streak (consecutive days)")
        self.show_streak.setChecked(True)
        layout.addWidget(self.show_streak)

        self.show_focus_score = QCheckBox("Show daily focus score")
        self.show_focus_score.setChecked(True)
        layout.addWidget(self.show_focus_score)

        self.show_motivational = QCheckBox("Show motivational quotes")
        self.show_motivational.setChecked(True)
        layout.addWidget(self.show_motivational)

        layout.addStretch()

        hint = _body(
            "Tip: A personalized blocking page is more effective at building "
            "good habits than a generic one."
        )
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self.setLayout(layout)


# ═══════════════════════════════════════════════════════════════════════════
# Page 5: Domain Manager
# ═══════════════════════════════════════════════════════════════════════════

class DomainManagerPage(QWizardPage):
    """Domain management page — view/edit all domains, categories, budgets."""

    _COL_DOMAIN = 0
    _COL_CATEGORY = 1
    _COL_STATUS = 2
    _COL_BUDGET = 3
    _COL_USED = 4
    _COL_OVERRIDES = 5
    _COLUMNS = ["Domain", "Category", "Status", "Daily Budget", "Used Today", "Overrides"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Domain Manager")
        self.setSubTitle("View and manage domain categories, budgets, and blocking rules.")

        layout = QVBoxLayout()

        # --- Master budget display ---
        master_row = QHBoxLayout()
        master_row.addWidget(QLabel("Master distraction budget:"))
        self.master_budget_spin = QSpinBox()
        self.master_budget_spin.setRange(5, 480)
        self.master_budget_spin.setSuffix(" min")
        self.master_budget_spin.setValue(45)
        master_row.addWidget(self.master_budget_spin)
        master_row.addStretch()
        layout.addLayout(master_row)

        layout.addWidget(_separator())

        # --- Search bar ---
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter domains...")
        self.search_box.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        # Category filter (tabs without separate pages — one shared table below)
        self._all_domains: list = []
        self._categories: list = []
        self._current_tab_category: str = ""  # "" = All

        self.category_bar = QTabBar()
        self.category_bar.setExpanding(False)
        self.category_bar.addTab("All")
        self.category_bar.currentChanged.connect(self._on_category_tab_changed)
        layout.addWidget(self.category_bar)

        self.domain_table = QTableWidget(0, len(self._COLUMNS))
        self.domain_table.setHorizontalHeaderLabels(self._COLUMNS)
        self.domain_table.horizontalHeader().setSectionResizeMode(
            self._COL_DOMAIN, QHeaderView.Stretch
        )
        self.domain_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.domain_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.domain_table.setAlternatingRowColors(True)
        layout.addWidget(self.domain_table)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add Domain")
        self.btn_add.clicked.connect(self._on_add_domain)
        btn_row.addWidget(self.btn_add)

        self.btn_allow = QPushButton("Allow")
        self.btn_allow.clicked.connect(lambda: self._set_selected_status("allowed"))
        btn_row.addWidget(self.btn_allow)

        self.btn_block = QPushButton("Block")
        self.btn_block.clicked.connect(lambda: self._set_selected_status("blocked"))
        btn_row.addWidget(self.btn_block)

        self.btn_set_budget = QPushButton("Set Budget")
        self.btn_set_budget.clicked.connect(self._on_set_budget)
        btn_row.addWidget(self.btn_set_budget)

        self.btn_change_cat = QPushButton("Change Category")
        self.btn_change_cat.clicked.connect(self._on_change_category)
        btn_row.addWidget(self.btn_change_cat)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def initializePage(self):
        """Called when the page is shown — load data from DomainConfigManager."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            self._all_domains = mgr.get_all_known_domains()

            # Enrich with usage (best-effort)
            try:
                import requests
                resp = requests.get(f"{resolve_tab_server_base_url()}/api/domains/overview", timeout=2)
                if resp.ok:
                    self._all_domains = resp.json().get("domains", self._all_domains)
            except Exception:
                pass

            # Build category tabs
            cats = sorted({d.get("category", "unknown") for d in self._all_domains})
            self._categories = cats
            self.category_bar.blockSignals(True)
            while self.category_bar.count():
                self.category_bar.removeTab(0)
            self.category_bar.addTab("All")
            for cat in cats:
                self.category_bar.addTab(cat.replace("_", " ").title())
            self.category_bar.setCurrentIndex(0)
            self.category_bar.blockSignals(False)

            # Load master budget
            mb = mgr.get_master_budget()
            self.master_budget_spin.setValue(
                mb.get("max_total_distraction_seconds", 2700) // 60
            )

            self._populate_table(self._all_domains)
            self._apply_filter(self.search_box.text())
        except Exception as e:
            logger.warning("Could not load domain data: %s", e)

    def _populate_table(self, domains: list) -> None:
        """Fill the table with domain data."""
        self.domain_table.setRowCount(len(domains))
        for row, d in enumerate(domains):
            # Domain
            self.domain_table.setItem(row, self._COL_DOMAIN,
                QTableWidgetItem(d.get("domain", "")))
            # Category
            self.domain_table.setItem(row, self._COL_CATEGORY,
                QTableWidgetItem(d.get("category", "unknown").replace("_", " ").title()))
            # Status
            status = d.get("status", "unknown")
            status_item = QTableWidgetItem(
                {"allowed": "✅ Allowed", "blocked": "🚫 Blocked",
                 "budgeted": "⏱️ Budgeted"}.get(status, status.title())
            )
            self.domain_table.setItem(row, self._COL_STATUS, status_item)
            # Budget
            rule = d.get("per_domain_rule", {})
            budget_secs = rule.get("max_cumulative_time_seconds", 0)
            budget_text = f"{budget_secs // 60} min" if budget_secs else "Default"
            self.domain_table.setItem(row, self._COL_BUDGET,
                QTableWidgetItem(budget_text))
            # Used today
            used = d.get("time_used_today_seconds", 0)
            used_text = f"{int(used) // 60}m {int(used) % 60}s" if used else "0m"
            self.domain_table.setItem(row, self._COL_USED,
                QTableWidgetItem(used_text))
            # Overrides
            overrides = d.get("overrides_used_today", 0)
            self.domain_table.setItem(row, self._COL_OVERRIDES,
                QTableWidgetItem(str(overrides)))

    def _apply_filter(self, text: str) -> None:
        """Filter table rows by search text."""
        text = text.lower()
        for row in range(self.domain_table.rowCount()):
            item = self.domain_table.item(row, self._COL_DOMAIN)
            domain = item.text().lower() if item else ""
            cat_item = self.domain_table.item(row, self._COL_CATEGORY)
            cat = cat_item.text().lower() if cat_item else ""
            visible = text in domain or text in cat
            self.domain_table.setRowHidden(row, not visible)

    def _on_category_tab_changed(self, index: int) -> None:
        """Filter table rows by category tab (shared domain_table)."""
        if index == 0:
            # All
            self._current_tab_category = ""
            self._populate_table(self._all_domains)
        elif index - 1 < len(self._categories):
            cat = self._categories[index - 1]
            self._current_tab_category = cat
            filtered = [d for d in self._all_domains if d.get("category") == cat]
            self._populate_table(filtered)
        self._apply_filter(self.search_box.text())

    def _get_selected_domains(self) -> list:
        """Return list of selected domain strings."""
        rows = set(idx.row() for idx in self.domain_table.selectedIndexes())
        result = []
        for row in rows:
            item = self.domain_table.item(row, self._COL_DOMAIN)
            if item:
                result.append(item.text())
        return result

    def _on_add_domain(self) -> None:
        """Add a new domain via dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Domain")
        dlg_layout = QVBoxLayout()

        dlg_layout.addWidget(QLabel("Domain:"))
        domain_input = QLineEdit()
        domain_input.setPlaceholderText("e.g. example.com")
        dlg_layout.addWidget(domain_input)

        dlg_layout.addWidget(QLabel("Category:"))
        cat_combo = QComboBox()
        cat_combo.addItems(self._categories if self._categories else [
            "social_media", "entertainment", "gaming", "news", "shopping",
            "education", "productivity", "development", "work", "email",
        ])
        dlg_layout.addWidget(cat_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)
        dlg.setLayout(dlg_layout)

        if dlg.exec_() == QDialog.Accepted:
            domain = domain_input.text().strip().lower()
            category = cat_combo.currentText()
            if domain:
                try:
                    from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
                    mgr = get_domain_config_manager()
                    mgr.add_domain_to_category(domain, category)
                    self.initializePage()  # Refresh
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to add domain: {e}")

    def _set_selected_status(self, status: str) -> None:
        """Allow or block selected domains."""
        domains = self._get_selected_domains()
        if not domains:
            return
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()
            for d in domains:
                if status == "allowed":
                    mgr.add_always_allowed_domain(d)
                elif status == "blocked":
                    mgr.remove_always_allowed_domain(d)
            self.initializePage()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_set_budget(self) -> None:
        """Set budget for selected domains."""
        domains = self._get_selected_domains()
        if not domains:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Set Budget for {len(domains)} domain(s)")
        dlg_layout = QFormLayout()

        budget_spin = QSpinBox()
        budget_spin.setRange(1, 480)
        budget_spin.setValue(15)
        budget_spin.setSuffix(" min")
        dlg_layout.addRow("Daily budget:", budget_spin)

        overrides_spin = QSpinBox()
        overrides_spin.setRange(1, 50)
        overrides_spin.setValue(3)
        dlg_layout.addRow("Max overrides/day:", overrides_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addRow(buttons)
        dlg.setLayout(dlg_layout)

        if dlg.exec_() == QDialog.Accepted:
            try:
                from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
                mgr = get_domain_config_manager()
                rule = {
                    "max_cumulative_time_seconds": budget_spin.value() * 60,
                    "max_overrides_per_day": overrides_spin.value(),
                    "max_override_duration_seconds": 300,
                    "penalty_per_extra_override_seconds": 60,
                }
                for d in domains:
                    mgr.set_per_domain_rule(d, rule)
                self.initializePage()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _on_change_category(self) -> None:
        """Change category for selected domains."""
        domains = self._get_selected_domains()
        if not domains:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Change Category for {len(domains)} domain(s)")
        dlg_layout = QVBoxLayout()

        dlg_layout.addWidget(QLabel("New category:"))
        cat_combo = QComboBox()
        cat_combo.addItems(self._categories if self._categories else [
            "social_media", "entertainment", "gaming", "news", "shopping",
            "education", "productivity", "development", "work", "email",
        ])
        dlg_layout.addWidget(cat_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)
        dlg.setLayout(dlg_layout)

        if dlg.exec_() == QDialog.Accepted:
            try:
                from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
                mgr = get_domain_config_manager()
                mgr.move_domains_to_category(domains, cat_combo.currentText())
                self.initializePage()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def get_master_budget_seconds(self) -> int:
        """Return the master budget value in seconds."""
        return self.master_budget_spin.value() * 60


# ═══════════════════════════════════════════════════════════════════════════
# Page 6b: Admin Password Setup
# ═══════════════════════════════════════════════════════════════════════════

class PasswordPage(QWizardPage):
    """Page for setting the admin/parental password to protect enforcement mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Admin Password")
        self.setSubTitle("Protect Focus Guard settings with a password (recommended).")

        layout = QVBoxLayout()

        layout.addWidget(_body(
            "Setting an admin password prevents the monitored user from weakening "
            "Focus Guard — for example, switching from 'Enforcing' to 'Tracking' mode "
            "or changing time budgets without authorization.\n\n"
            "This is strongly recommended if you are setting up Focus Guard for a child "
            "or student."
        ))

        layout.addWidget(_separator())

        self.enable_password = QCheckBox("Enable admin password protection")
        self.enable_password.setChecked(True)
        self.enable_password.toggled.connect(self._toggle_fields)
        layout.addWidget(self.enable_password)

        # --- Password fields ---
        self.password_group = QGroupBox("Set Password")
        pw_layout = QFormLayout()

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Enter a strong password")
        self.password.setToolTip("At least 4 characters. Choose something the monitored user won't guess.")
        self.password.textChanged.connect(self._validate_passwords)
        pw_layout.addRow("Password:", self.password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setPlaceholderText("Re-enter password")
        self.confirm_password.textChanged.connect(self._validate_passwords)
        pw_layout.addRow("Confirm:", self.confirm_password)

        self.show_passwords_cb = QCheckBox("Show passwords")
        self.show_passwords_cb.setToolTip("Temporarily show what you typed (look away if someone is watching).")
        self.show_passwords_cb.toggled.connect(self._toggle_show_passwords)
        pw_layout.addRow("", self.show_passwords_cb)

        self.password_group.setLayout(pw_layout)
        layout.addWidget(self.password_group)

        self._existing_password_hash: str = ""

        # --- Validation feedback ---
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #cc0000; font-size: 11px;")
        layout.addWidget(self.validation_label)

        layout.addStretch()

        hint = _body(
            "💡 Tip: Remember this password! You'll need it to change enforcement mode, "
            "modify time budgets, or log into the admin dashboard.\n"
            "You can change or remove it later using the command:\n"
            "  focus-guard set-password  /  focus-guard remove-password"
        )
        hint.setStyleSheet("color: #0066cc; background-color: #e6f2ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def set_existing_password_hash(self, password_hash: str) -> None:
        """When re-opening the wizard, avoid forcing a password reset if fields stay empty."""
        self._existing_password_hash = (password_hash or "").strip()

    def _toggle_show_passwords(self, visible: bool) -> None:
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        self.password.setEchoMode(mode)
        self.confirm_password.setEchoMode(mode)

    def _toggle_fields(self, enabled: bool):
        self.password_group.setEnabled(enabled)
        if not enabled:
            self.validation_label.setText("")
        self._validate_passwords()

    def _validate_passwords(self):
        """Update the validation label based on current input."""
        if not self.enable_password.isChecked():
            self.validation_label.setText("")
            self.completeChanged.emit()
            return

        pw = self.password.text()
        cpw = self.confirm_password.text()

        if (
            self._existing_password_hash
            and not pw.strip()
            and not cpw.strip()
        ):
            self.validation_label.setText("Keeping existing admin password — enter below only if you want to replace it.")
            self.validation_label.setStyleSheet("color: #666; font-size: 11px;")
            self.completeChanged.emit()
            return

        if not pw:
            self.validation_label.setText("")
        elif len(pw) < 4:
            self.validation_label.setText("Password must be at least 4 characters.")
            self.validation_label.setStyleSheet("color: #cc0000; font-size: 11px;")
        elif cpw and pw != cpw:
            self.validation_label.setText("Passwords do not match.")
            self.validation_label.setStyleSheet("color: #cc0000; font-size: 11px;")
        elif cpw and pw == cpw:
            self.validation_label.setText("Passwords match.")
            self.validation_label.setStyleSheet("color: #008800; font-size: 11px;")
        else:
            self.validation_label.setText("")

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        """Only allow Next if password is valid (or disabled)."""
        if not self.enable_password.isChecked():
            return True
        pw = self.password.text().strip()
        cpw = self.confirm_password.text().strip()
        if self._existing_password_hash and not pw and not cpw:
            return True
        return len(pw) >= 4 and pw == cpw

    def get_password_hash(self) -> str:
        """Return SHA-256 hash; preserve prior hash when user leaves fields blank."""
        if not self.enable_password.isChecked():
            return ""
        import hashlib

        pw = self.password.text().strip()
        cpw = self.confirm_password.text().strip()
        if self._existing_password_hash and not pw and not cpw:
            return self._existing_password_hash
        return hashlib.sha256(pw.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# Page 7: Startup & Finish
# ═══════════════════════════════════════════════════════════════════════════

class FinishPage(QWizardPage):
    def __init__(self, parent=None, standalone_setup_only: bool = False):
        super().__init__(parent)
        self.setTitle("You're All Set!")
        self.setSubTitle("Focus Guard is ready to go.")

        layout = QVBoxLayout()

        if standalone_setup_only:
            layout.addWidget(_body(
                "• Use Save setup anytime to save to disk without leaving this wizard.\n"
                '• Save & launch Focus Guard saves and tries to start the full app (same as '
                "running python -m focus_guard.main from your project folder).\n\n"
                "If launch fails, open a terminal there and run that command manually."
            ))
        else:
            layout.addWidget(_body(
                "Here's what will happen next:\n\n"
                "  • Focus Guard will run in the system tray\n"
                "  • The tab server will monitor browser activity\n"
                "  • Activity reports will be sent per your schedule\n"
                "  • Distracting sites will be blocked based on your rules\n\n"
                "On this page, use Save setup anytime to persist without starting services yet "
                '(then click Start Focus Guard).\nYou can change settings later from the tray icon.'
            ))

        layout.addWidget(_separator())

        dash_url = admin_dashboard_http_url()
        if standalone_setup_only:
            finish_title = "When you launch the full app"
            finish_body = (
                "Run  python -m focus_guard.main  as described above.\n\n"
                "The guardian dashboard is not reachable until that process has started. "
                "About two seconds after the tray icon appears, a \"Finish setup\" window opens "
                "— use Open Guardian Dashboard and Run connection check there.\n\n"
                f"Dashboard URL (bookmark after it loads): {dash_url}"
            )
        else:
            finish_title = "After you click Start Focus Guard"
            finish_body = (
                "The guardian dashboard is not reachable from this wizard because local services "
                "have not finished starting yet.\n\n"
                'About two seconds after the tray icon appears, a small "Finish setup" window opens. '
                "Use Open Guardian Dashboard and Run connection check there—not from this screen.\n\n"
                f"Dashboard URL (bookmark after it loads): {dash_url}"
            )

        finish_group = QGroupBox(finish_title)
        finish_hint = QVBoxLayout()
        finish_hint.addWidget(_body(finish_body))
        finish_group.setLayout(finish_hint)
        layout.addWidget(finish_group)

        layout.addWidget(_separator())

        # --- Enforcement mode ---
        mode_group = QGroupBox("Enforcement Mode")
        mode_layout = QVBoxLayout()

        mode_layout.addWidget(_body(
            "Choose how Focus Guard handles distracting sites:"
        ))

        self.enforcement_mode = QComboBox()
        self.enforcement_mode.addItems(["Enforcing", "Advisory", "Tracking"])
        self.enforcement_mode.setCurrentIndex(0)  # Default: Enforcing
        mode_layout.addWidget(self.enforcement_mode)

        mode_desc = _body(
            "\u2022 Enforcing \u2014 Block distracting sites and enforce time budgets (recommended)\n"
            "\u2022 Advisory \u2014 Log activity and show notifications, but don't block\n"
            "\u2022 Tracking \u2014 Silently log all activity without any blocking or notifications"
        )
        mode_desc.setStyleSheet("color: #555; font-size: 11px;")
        mode_layout.addWidget(mode_desc)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        layout.addWidget(_separator())

        self.autostart_cb = QCheckBox("Start Focus Guard automatically when Windows starts")
        self.autostart_cb.setChecked(True)
        layout.addWidget(self.autostart_cb)

        self.minimize_cb = QCheckBox("Minimize to tray on startup (no window)")
        self.minimize_cb.setChecked(True)
        layout.addWidget(self.minimize_cb)

        layout.addStretch()

        self.setLayout(layout)


# ═══════════════════════════════════════════════════════════════════════════
# Wizard
# ═══════════════════════════════════════════════════════════════════════════

class FirstRunWizard(QWizard):
    """Multi-page first-run setup wizard."""

    def __init__(
        self,
        icon: Optional[QIcon] = None,
        parent=None,
        *,
        standalone_setup_only: bool = False,
        settings_mode: bool = False,
    ):
        super().__init__(parent)
        if standalone_setup_only and settings_mode:
            raise ValueError("standalone_setup_only and settings_mode are mutually exclusive")
        self._standalone_setup_only = standalone_setup_only
        self._settings_mode = settings_mode
        self.setWindowTitle("Focus Guard Setup")

        self.setOption(QWizard.HaveCustomButton1, True)
        self.setButtonText(QWizard.CustomButton1, "Save setup")
        self.customButtonClicked.connect(self._on_custom_dialog_button)
        self.currentIdChanged.connect(self._sync_wizard_buttons)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(800, 600)

        if icon and not icon.isNull():
            self.setWindowIcon(icon)

        # Pages
        self.welcome_page = WelcomePage()
        self.email_page = EmailPage()
        self.extension_page = ExtensionPage()
        self.time_limits_page = TimeLimitsPage()
        self.personalization_page = PersonalizationPage()
        self.domain_manager_page = DomainManagerPage()
        self.password_page = PasswordPage()
        self.finish_page = FinishPage(standalone_setup_only=standalone_setup_only)

        self.addPage(self.welcome_page)
        self.addPage(self.email_page)
        self.addPage(self.extension_page)
        self.addPage(self.time_limits_page)
        self.addPage(self.personalization_page)
        self.addPage(self.domain_manager_page)
        self.addPage(self.password_page)
        self.addPage(self.finish_page)

        from focus_guard.deployment.config import DeploymentConfig

        if DeploymentConfig.get_config_path().exists():
            self.apply_saved_deployment_config()

        self._sync_wizard_buttons()

    def _sync_wizard_buttons(self, _page_id: int = None) -> None:
        btn_custom = self.button(QWizard.CustomButton1)
        on_finish = self.currentPage() is self.finish_page
        btn_custom.setVisible(on_finish)
        if not on_finish:
            return
        if self._settings_mode:
            self.setButtonText(QWizard.FinishButton, "Save Settings")
        elif self._standalone_setup_only:
            self.setButtonText(QWizard.FinishButton, "Save & launch Focus Guard")
        else:
            self.setButtonText(QWizard.FinishButton, "Start Focus Guard")

    def _on_custom_dialog_button(self, which: int) -> None:
        if which != QWizard.CustomButton1:
            return
        if self.save_setup_to_disk():
            if self._settings_mode:
                msg = (
                    "Settings saved.\nUse Save Settings when finished, or Save setup again anytime."
                )
            elif self._standalone_setup_only:
                msg = (
                    "Setup saved.\nContinue editing here if needed, "
                    'then choose Save & launch Focus Guard—or run python -m focus_guard.main.'
                )
            else:
                msg = (
                    "Setup saved.\nContinue editing if needed, then click Start Focus Guard when "
                    "you are ready for the tray and services."
                )
            QMessageBox.information(self, "Focus Guard", msg)

    def save_setup_to_disk(self) -> bool:
        """Write current wizard state to deployment + domain configs without completing the wizard."""
        try:
            config = self.get_config()
            config.save()
            logger.info(
                "Setup saved without finishing wizard (%s)",
                config.get_config_path(),
            )
            return True
        except Exception as e:
            logger.exception("Could not save setup: %s", e)
            QMessageBox.warning(self, "Focus Guard", f"Could not save setup:\n{e}")
            return False

    def apply_saved_deployment_config(self) -> bool:
        """Populate wizard fields when deployment_config.json already exists (reuse during testing/settings)."""

        from focus_guard.deployment.config import DeploymentConfig

        cfg_path = DeploymentConfig.get_config_path()
        if not cfg_path.exists():
            return False
        try:
            cfg = DeploymentConfig.load()
        except Exception as exc:
            logger.warning("Could not prefill wizard from saved config: %s", exc)
            return False

        ep = self.email_page
        ep.enable_email.setChecked(cfg.email.enabled)
        ep.smtp_server.setText(cfg.email.smtp_server)
        ep.smtp_port.setValue(cfg.email.smtp_port)
        ep.smtp_user.setText(cfg.email.smtp_username)
        ep.smtp_pass.setText(cfg.email.smtp_password)
        ep.recipients.setText(", ".join(cfg.email.recipients))

        interval = cfg.reporting.schedule.get_hourly_interval_minutes()
        combo_intervals = [5, 60, 120, 240, 1440]
        best_i = min(
            range(len(combo_intervals)),
            key=lambda i: abs(combo_intervals[i] - interval),
        )
        ep.frequency.setCurrentIndex(best_i)

        fp = self.finish_page
        fp.autostart_cb.setChecked(cfg.run_at_startup)
        mode_index = {"enforcing": 0, "advisory": 1, "tracking": 2}.get(
            cfg.enforcement_mode, 0
        )
        fp.enforcement_mode.setCurrentIndex(mode_index)

        pp = self.personalization_page
        pp.display_name.setText(cfg.popup.user_display_name)
        tone_index = {"encouraging": 0, "firm": 1, "playful": 2}.get(cfg.popup.tone, 0)
        pp.tone.setCurrentIndex(tone_index)
        pp.show_streak.setChecked(cfg.popup.show_streak)
        pp.show_focus_score.setChecked(cfg.popup.show_focus_score)
        pp.show_motivational.setChecked(cfg.popup.show_motivational_message)

        self.extension_page.extension_installed_cb.setChecked(
            getattr(cfg, "wizard_extension_acknowledged", False),
        )

        if cfg.config_password_hash:
            self.password_page.enable_password.setChecked(True)
            self.password_page.set_existing_password_hash(cfg.config_password_hash)
        else:
            self.password_page.enable_password.setChecked(False)
            self.password_page.set_existing_password_hash("")

        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager

            mgr = get_domain_config_manager()
            mb = mgr.get_master_budget()
            tlp = self.time_limits_page
            tlp.master_budget.setValue(
                max(5, int(mb.get("max_total_distraction_seconds", 2700)) // 60)
            )
            cat_budgets = mgr.get_classification_budgets()

            def fill_cat(key: str, spin_widget, fallback_minutes: int) -> None:
                rule = cat_budgets.get(key, {}) or {}
                secs = int(
                    rule.get("max_cumulative_time_seconds", fallback_minutes * 60)
                    or (fallback_minutes * 60)
                )
                spin_widget.setValue(max(0, secs // 60))

            fill_cat("ENTERTAINMENT:DISTRACTION", tlp.entertainment_budget, 30)
            fill_cat("SOCIAL_MEDIA:DISTRACTION", tlp.social_media_budget, 20)
            fill_cat("GAMING:DISTRACTION", tlp.gaming_budget, 15)

            ov_src = (
                cat_budgets.get("ENTERTAINMENT:DISTRACTION")
                or cat_budgets.get("SOCIAL_MEDIA:DISTRACTION")
                or {}
            )
            tlp.max_overrides.setValue(int(ov_src.get("max_overrides_per_day", 3) or 3))
            od_sec = int(ov_src.get("max_override_duration_seconds", 300) or 300)
            tlp.override_duration.setValue(max(1, od_sec // 60))
        except Exception as exc:
            logger.warning("Could not prefill time-limit fields from domain config: %s", exc)

        self.password_page._validate_passwords()
        return True

    def get_config(self):
        """Build a DeploymentConfig from the wizard fields."""
        from focus_guard.deployment.config import (
            DeploymentConfig,
            EmailConfig,
            PopupConfig,
            ReportingConfig,
            ScheduleConfig,
            StorageConfig,
            MonitoringConfig,
        )

        try:
            prev = DeploymentConfig.load()
            persist_tab_host = prev.tab_server_host
            persist_tab_port = prev.tab_server_port
            persist_run_as_service = prev.run_as_service
            persist_hide = prev.hide_from_user
            persist_require_admin = prev.require_admin_to_stop
        except Exception:
            persist_tab_host = "127.0.0.1"
            persist_tab_port = 58392
            persist_run_as_service = True
            persist_hide = False
            persist_require_admin = True

        # Email
        email_enabled = self.email_page.enable_email.isChecked()
        email = EmailConfig(
            enabled=email_enabled,
            smtp_server=self.email_page.smtp_server.text().strip(),
            smtp_port=self.email_page.smtp_port.value(),
            smtp_username=self.email_page.smtp_user.text().strip(),
            smtp_password=self.email_page.smtp_pass.text().strip(),
            use_tls=True,
            sender_email=self.email_page.smtp_user.text().strip(),
            sender_name="FocusGuard Monitor",
            recipients=[
                r.strip()
                for r in self.email_page.recipients.text().split(",")
                if r.strip()
            ],
        )

        # Schedule from frequency combo
        freq_minutes_map = {
            0: 5,      # Every 5 minutes (testing)
            1: 60,     # Hourly
            2: 120,    # Every 2 hours
            3: 240,    # Every 4 hours
            4: 1440,   # Daily
        }
        interval_minutes = freq_minutes_map.get(self.email_page.frequency.currentIndex(), 60)
        schedule = ScheduleConfig(
            hourly_enabled=True,
            hourly_interval_minutes=interval_minutes,
            hourly_interval_hours=max(1, interval_minutes // 60),
            daily_enabled=(interval_minutes >= 1440),
        )

        reporting = ReportingConfig(
            hourly_report=True,
            daily_report=True,
            report_frequency="hourly",
            schedule=schedule,
        )

        # Enforcement mode from combo box
        mode_map = {0: "enforcing", 1: "advisory", 2: "tracking"}
        enforcement_mode = mode_map.get(
            self.finish_page.enforcement_mode.currentIndex(), "enforcing"
        )

        # Popup personalization
        tone_map = {0: "encouraging", 1: "firm", 2: "playful"}
        popup = PopupConfig(
            user_display_name=self.personalization_page.display_name.text().strip(),
            tone=tone_map.get(self.personalization_page.tone.currentIndex(), "encouraging"),
            show_streak=self.personalization_page.show_streak.isChecked(),
            show_focus_score=self.personalization_page.show_focus_score.isChecked(),
            show_motivational_message=self.personalization_page.show_motivational.isChecked(),
        )

        # Admin password
        password_hash = self.password_page.get_password_hash()

        config = DeploymentConfig(
            machine_name=socket.gethostname(),
            email=email,
            reporting=reporting,
            storage=StorageConfig(),
            monitoring=MonitoringConfig(),
            popup=popup,
            enforcement_mode=enforcement_mode,
            tab_server_host=persist_tab_host,
            tab_server_port=persist_tab_port,
            run_at_startup=self.finish_page.autostart_cb.isChecked(),
            run_as_service=persist_run_as_service,
            hide_from_user=persist_hide,
            require_admin_to_stop=persist_require_admin,
            config_password_hash=password_hash,
            wizard_extension_acknowledged=self.extension_page.extension_installed_cb.isChecked(),
        )

        # Save time limits and budgets to DomainConfigManager
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            # Master budget from time limits page (takes precedence over domain manager page)
            mb = mgr.get_master_budget()
            mb["max_total_distraction_seconds"] = self.time_limits_page.master_budget.value() * 60
            mgr.set_master_budget(mb)

            # Per-category budgets from time limits page
            cat_budgets = mgr.get_classification_budgets()

            # Entertainment budget
            ent_key = "ENTERTAINMENT:DISTRACTION"
            if ent_key not in cat_budgets:
                cat_budgets[ent_key] = {}
            cat_budgets[ent_key]["max_cumulative_time_seconds"] = self.time_limits_page.entertainment_budget.value() * 60
            cat_budgets[ent_key]["max_overrides_per_day"] = self.time_limits_page.max_overrides.value()
            cat_budgets[ent_key]["max_override_duration_seconds"] = self.time_limits_page.override_duration.value() * 60

            # Social media budget
            sm_key = "SOCIAL_MEDIA:DISTRACTION"
            if sm_key not in cat_budgets:
                cat_budgets[sm_key] = {}
            cat_budgets[sm_key]["max_cumulative_time_seconds"] = self.time_limits_page.social_media_budget.value() * 60
            cat_budgets[sm_key]["max_overrides_per_day"] = self.time_limits_page.max_overrides.value()
            cat_budgets[sm_key]["max_override_duration_seconds"] = self.time_limits_page.override_duration.value() * 60

            # Gaming budget
            game_key = "GAMING:DISTRACTION"
            if game_key not in cat_budgets:
                cat_budgets[game_key] = {}
            cat_budgets[game_key]["max_cumulative_time_seconds"] = self.time_limits_page.gaming_budget.value() * 60
            cat_budgets[game_key]["max_overrides_per_day"] = self.time_limits_page.max_overrides.value()
            cat_budgets[game_key]["max_override_duration_seconds"] = self.time_limits_page.override_duration.value() * 60

            # Save all category budgets
            for key, budget in cat_budgets.items():
                mgr.set_classification_budget(key, budget)

            logger.info("Saved time limits from wizard: master=%d min, ent=%d min, social=%d min, gaming=%d min",
                        self.time_limits_page.master_budget.value(),
                        self.time_limits_page.entertainment_budget.value(),
                        self.time_limits_page.social_media_budget.value(),
                        self.time_limits_page.gaming_budget.value())

        except Exception as e:
            logger.warning("Could not save time limits from wizard: %s", e)

        return config


def launch_focus_guard_main_detached() -> None:
    """Start ``python -m focus_guard.main`` with cwd at the checkout root (development)."""
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [sys.executable, "-m", "focus_guard.main"]
    if os.name == "nt" and hasattr(subprocess, "DETACHED_PROCESS"):
        subprocess.Popen(cmd, cwd=str(repo_root), creationflags=subprocess.DETACHED_PROCESS)
    else:
        subprocess.Popen(cmd, cwd=str(repo_root))


def is_first_run() -> bool:
    """Return True if no deployment config exists yet."""
    from focus_guard.deployment.config import DeploymentConfig
    return not DeploymentConfig.get_config_path().exists()


def run_first_run_wizard(
    icon: Optional[QIcon] = None,
    *,
    standalone_setup_only: bool = False,
) -> Optional[object]:
    """Show the wizard and return the saved DeploymentConfig, or None if cancelled.

    If *standalone_setup_only* is True (wizard run via ``first_run_wizard.py``), finishing
    with **Save & launch Focus Guard** also attempts to start ``python -m focus_guard.main``.
    Users can tap **Save setup** anytime to persist JSON without leaving the wizard.
    """
    wizard = FirstRunWizard(icon=icon, standalone_setup_only=standalone_setup_only)
    result = wizard.exec_()

    if result == QWizard.Accepted:
        config = wizard.get_config()
        try:
            config.save()
            logger.info("First-run config saved to %s", config.get_config_path())
        except Exception as e:
            logger.error("Failed to save first-run config: %s", e)
            QMessageBox.warning(
                None,
                "Focus Guard",
                f"Could not save configuration:\n{e}\n\nDefault settings will be used.",
            )
        else:
            if standalone_setup_only:
                try:
                    launch_focus_guard_main_detached()
                except OSError as e:
                    logger.exception("Could not spawn focus_guard.main: %s", e)
                    QMessageBox.warning(
                        None,
                        "Focus Guard",
                        "Could not start Focus Guard automatically.\n\n"
                        "Open a terminal in your project folder and run:\n"
                        "    python -m focus_guard.main",
                    )
        return config

    logger.info("First-run wizard cancelled — using defaults")
    return None


if __name__ == "__main__":
    # Supports: `python focus_guard/gui/first_run_wizard.py` from repo root.
    import sys
    from pathlib import Path

    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    logging.basicConfig(level=logging.INFO)

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    config = run_first_run_wizard(standalone_setup_only=True)
    raise SystemExit(0 if config is not None else 1)
