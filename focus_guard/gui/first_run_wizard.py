"""
Focus Guard — First-Run Setup Wizard (PyQt5).

Shown on first launch when no deployment_config.json exists.
Walks the user through: Welcome → Email → Extension → Done.
Saves a DeploymentConfig at the end.
"""

import json
import logging
import socket
import sys
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen
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

logger = logging.getLogger(__name__)


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
            "These settings tell Focus Guard how to send emails. "
            "For Gmail, use smtp.gmail.com with port 587 and an App Password."
        )
        smtp_desc.setStyleSheet("color: #555; font-size: 11px;")
        smtp_layout.addWidget(smtp_desc)

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
        self.smtp_user.setPlaceholderText("your.email@gmail.com")
        self.smtp_user.setToolTip("Your full email address (this is the 'From' address)")
        form.addRow("Your Email:", self.smtp_user)

        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_pass.setPlaceholderText("App password (not your login password)")
        self.smtp_pass.setToolTip("For Gmail: create an App Password at myaccount.google.com → Security")
        form.addRow("App Password:", self.smtp_pass)

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
            "💡 Tip: For Gmail, you need an App Password (not your regular password).\n"
            "Go to myaccount.google.com → Security → 2-Step Verification → App passwords."
        )
        hint.setStyleSheet("color: #0066cc; background-color: #e6f2ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def _toggle_fields(self, enabled: bool):
        self.smtp_group.setEnabled(enabled)
        self.recip_group.setEnabled(enabled)
        self.frequency.setEnabled(enabled)


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

        self.password_group.setLayout(pw_layout)
        layout.addWidget(self.password_group)

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
        pw = self.password.text()
        cpw = self.confirm_password.text()
        return len(pw) >= 4 and pw == cpw

    def get_password_hash(self) -> str:
        """Return the SHA-256 hash of the password, or empty string if disabled."""
        if not self.enable_password.isChecked():
            return ""
        import hashlib
        return hashlib.sha256(self.password.text().encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# Page 7: Startup & Finish
# ═══════════════════════════════════════════════════════════════════════════

class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("You're All Set!")
        self.setSubTitle("Focus Guard is ready to go.")
        self._validation_level = "warn"

        layout = QVBoxLayout()

        layout.addWidget(_body(
            "Here's what will happen next:\n\n"
            "  • Focus Guard will run in the system tray\n"
            "  • The tab server will monitor browser activity\n"
            "  • Activity reports will be sent per your schedule\n"
            "  • Distracting sites will be blocked based on your rules\n\n"
            "You can always change settings by right-clicking the tray icon."
        ))

        layout.addWidget(_separator())

        # --- Guardian/Admin Dashboard handoff ---
        admin_group = QGroupBox("Parent/Guardian Dashboard")
        admin_layout = QVBoxLayout()
        admin_url = "http://127.0.0.1:58393/admin"
        admin_layout.addWidget(
            _body(
                "Use the Guardian Dashboard to review activity, adjust rules, and manage settings.\n"
                f"Dashboard URL: {admin_url}"
            )
        )
        open_dashboard_btn = QPushButton("Open Guardian Dashboard")
        open_dashboard_btn.setToolTip("Opens the local admin dashboard in your default browser")
        open_dashboard_btn.clicked.connect(lambda: webbrowser.open(admin_url))
        admin_layout.addWidget(open_dashboard_btn)
        admin_group.setLayout(admin_layout)
        layout.addWidget(admin_group)

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

        layout.addWidget(_separator())

        # --- Setup validation ---
        validation_group = QGroupBox("Setup Validation")
        validation_layout = QVBoxLayout()
        validation_layout.addWidget(_body(
            "Run validation before finishing setup. This checks extension readiness,\n"
            "live extension connectivity (via the tab server), admin protection, and local service health."
        ))

        self.validation_summary = QLabel("Validation not run yet.")
        self.validation_summary.setWordWrap(True)
        self.validation_summary.setStyleSheet("color: #9c6500;")
        validation_layout.addWidget(self.validation_summary)

        self.run_validation_btn = QPushButton("Run Setup Validation")
        self.run_validation_btn.clicked.connect(self._run_setup_validation)
        validation_layout.addWidget(self.run_validation_btn)
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)

        layout.addStretch()

        self.setLayout(layout)

    def initializePage(self):
        # Auto-run once so users see explicit readiness state.
        self._run_setup_validation()

    def _check_http_ok(self, url: str) -> bool:
        try:
            with urlopen(url, timeout=1.5) as resp:  # nosec B310 local endpoint check
                return 200 <= int(resp.status) < 300
        except (URLError, OSError, ValueError):
            return False

    def _fetch_json(self, url: str) -> Optional[dict]:
        try:
            with urlopen(url, timeout=2.0) as resp:  # nosec B310 local endpoint check
                if not (200 <= int(resp.status) < 300):
                    return None
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except (URLError, OSError, ValueError, json.JSONDecodeError):
            return None

    def _run_setup_validation(self):
        wizard = self.wizard()
        extension_ok = bool(
            getattr(getattr(wizard, "extension_page", None), "extension_installed_cb", None)
            and wizard.extension_page.extension_installed_cb.isChecked()
        )
        password_enabled = bool(
            getattr(getattr(wizard, "password_page", None), "enable_password", None)
            and wizard.password_page.enable_password.isChecked()
        )

        tab_base = resolve_tab_server_base_url()
        tab_health_ok = self._check_http_ok(f"{tab_base}/api/health")
        admin_health_ok = self._check_http_ok("http://127.0.0.1:58393/admin/health")

        status_payload: Optional[dict] = None
        auth_payload: Optional[dict] = None
        if tab_health_ok:
            status_payload = self._fetch_json(f"{tab_base}/api/status")
            auth_payload = self._fetch_json(f"{tab_base}/api/auth/status")

        extension_connected = False
        if isinstance(status_payload, dict):
            for b in status_payload.get("connected_browsers") or []:
                if isinstance(b, dict) and b.get("connected"):
                    extension_connected = True
                    break

        issues = []
        warnings = []

        if not extension_ok:
            issues.append("Extension install not confirmed.")
        if not password_enabled:
            warnings.append("Admin password is disabled (allowed, but less secure).")
        if not tab_health_ok:
            warnings.append("Tab server health endpoint not reachable yet.")
        if not admin_health_ok:
            warnings.append("Admin gateway health endpoint not reachable yet.")
        if tab_health_ok and isinstance(auth_payload, dict) and not auth_payload.get(
            "token_exists"
        ):
            warnings.append(
                "Tab server API auth token missing or unreadable — extensions may fail to authenticate."
            )
        if extension_ok and tab_health_ok and not extension_connected:
            warnings.append(
                "Extension install is confirmed but the tab server does not see a connected browser yet. "
                "Open Chrome or Edge, ensure Focus Guard is enabled on the store extension, browse any page — "
                "then click Run Setup Validation again."
            )

        if issues:
            self._validation_level = "not_ready"
            color = "#cc0000"
            title = "Not ready"
        elif warnings:
            self._validation_level = "warn"
            color = "#9c6500"
            title = "Ready with warnings"
        else:
            self._validation_level = "ready"
            color = "#008800"
            title = "Ready"

        lines = [f"<b>{title}</b>"]
        if issues:
            lines.extend([f"• {x}" for x in issues])
        if warnings:
            lines.extend([f"• {x}" for x in warnings])
        if not tab_health_ok or not admin_health_ok:
            lines.append(
                "• Wait a few seconds and click Run Setup Validation again; services start before this step on first launch."
            )

        self.validation_summary.setText("<br>".join(lines))
        self.validation_summary.setStyleSheet(f"color: {color};")
        self.completeChanged.emit()

    def validatePage(self) -> bool:
        self._run_setup_validation()
        if self._validation_level == "ready":
            return True
        if self._validation_level == "warn":
            reply = QMessageBox.question(
                self,
                "Setup Warnings",
                "Setup validation reported warnings. Continue and start Focus Guard anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            return reply == QMessageBox.Yes
        QMessageBox.warning(
            self,
            "Setup Not Ready",
            "Setup validation found blocking issues. Resolve them before finishing.",
        )
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Wizard
# ═══════════════════════════════════════════════════════════════════════════

class FirstRunWizard(QWizard):
    """Multi-page first-run setup wizard."""

    def __init__(self, icon: Optional[QIcon] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Focus Guard Setup")
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
        self.finish_page = FinishPage()

        self.addPage(self.welcome_page)
        self.addPage(self.email_page)
        self.addPage(self.extension_page)
        self.addPage(self.time_limits_page)
        self.addPage(self.personalization_page)
        self.addPage(self.domain_manager_page)
        self.addPage(self.password_page)
        self.addPage(self.finish_page)

        self.setButtonText(QWizard.FinishButton, "Start Focus Guard")

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
            run_at_startup=self.finish_page.autostart_cb.isChecked(),
            config_password_hash=password_hash,
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


def is_first_run() -> bool:
    """Return True if no deployment config exists yet."""
    from focus_guard.deployment.config import DeploymentConfig
    return not DeploymentConfig.get_config_path().exists()


def run_first_run_wizard(icon: Optional[QIcon] = None) -> Optional[object]:
    """Show the wizard and return the saved DeploymentConfig, or None if cancelled."""
    wizard = FirstRunWizard(icon=icon)
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
        return config

    logger.info("First-run wizard cancelled — using defaults")
    return None


if __name__ == "__main__":
    # Supports: `python focus_guard/gui/first_run_wizard.py` from repo root.
    # The wizard is normally shown from `python -m focus_guard.main` on first run.
    import sys
    from pathlib import Path

    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    logging.basicConfig(level=logging.INFO)

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    config = run_first_run_wizard()
    raise SystemExit(0 if config is not None else 1)
