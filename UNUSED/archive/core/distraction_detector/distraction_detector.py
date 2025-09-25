"""
DistractionDetector: Compares current activity to allowed list for the active task.
Implements distraction detection, alerting, logging, and learning hooks.
"""
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
import difflib
import sys
import re
import importlib

# Import logger
from core.logger.logger import get_logger

# Import domain classifier
from core.domain_classifier.domain_classifier import classify_domain
from core.domain_classifier.domain_utils import extract_domain_from_url, normalize_domain
from core.domain_classifier.domain_config import domain_config
from core.distraction_detector.browser_tracker import BrowserTabTracker

class DistractionRule:
    def check(self, active_window, top_windows, state) -> list:
        """Return a list of distraction events or an empty list."""
        raise NotImplementedError

class AreaIncreaseRule(DistractionRule):
    def check(self, active_window, top_windows, state):
        events = []
        prev = state.get('prev_top_windows_by_hwnd', {})
        for w in top_windows:
            hwnd = w.get('hwnd')
            if hwnd is not None and hwnd in prev:
                prev_percent = prev[hwnd].get('percent', 0)
                if w.get('percent', 0) > prev_percent + 0.2:  # 20% jump
                    events.append(f"Area increase: {w.get('app_name','')} ({prev_percent:.2f} -> {w.get('percent',0):.2f})")
        return events

class ContextSwitchRule(DistractionRule):
    def check(self, active_window, top_windows, state):
        events = []
        prev_active = state.get('prev_active_window')
        is_focus_app = state.get('is_focus_app')
        if prev_active and is_focus_app and is_focus_app(prev_active) and not is_focus_app(active_window):
            events.append(f"Context switch: {prev_active.get('app_name','')} -> {active_window.get('app_name','')}")
        return events

# URLRule will be imported later to avoid circular imports

class DistractionDetector:
    def __init__(
        self,
        allowed_apps: List[str],
        distraction_thresholds: Optional[Dict[str, int]] = None,
        user_overrides: Optional[Dict[str, bool]] = None,
        alert_callback: Optional[Callable[[Dict[str, str]], None]] = None,
        log_callback: Optional[Callable[[Dict[str, str]], None]] = None,
        config: Optional[Dict[str, Any]] = None,
        rules: Optional[List[DistractionRule]] = None
    ):
        """
        Initialize the distraction detector.
        - allowed_apps: list of allowed app/process names for the current task
        - distraction_thresholds: dict of app_name -> seconds before alert
        - user_overrides: dict of app_name -> is_allowed (user corrections)
        - alert_callback: function to call when a distraction is detected
        - log_callback: function to call for logging events
        - config: additional configuration (per-task/global)
        - rules: list of DistractionRule instances (for rule-based logic)
        """
        self.allowed_apps = set(allowed_apps)
        self.distraction_thresholds = distraction_thresholds or {}
        self.user_overrides = user_overrides or {}
        self.alert_callback = alert_callback
        self.log_callback = log_callback
        self.config = config or {}
        
        # Initialize domain whitelist and productive categories from config
        self.domain_whitelist = set(domain_config.get("whitelist", set()))
        self.productive_categories = self.config.get("productive_categories", ["work", "education", "productivity", "development", "email"])
        self.distracting_categories = self.config.get("distracting_categories", ["social", "entertainment", "shopping"])
        
        # Add custom domains to whitelist from config
        custom_whitelist = self.config.get("domain_whitelist", [])
        if custom_whitelist:
            self.domain_whitelist.update(custom_whitelist)
            
        # Initialize browser tab tracker
        self.browser_tracker = BrowserTabTracker(
            productive_categories=self.productive_categories,
            distracting_categories=self.distracting_categories,
            domain_whitelist=self.domain_whitelist
        )
            
        # Initialize basic rules first
        default_rules = [AreaIncreaseRule(), ContextSwitchRule()]
        
        # Import URLRule here to avoid circular imports
        from .url_rule import URLRule
        
        # Add URL rule
        default_rules.append(URLRule(self.productive_categories, self.distracting_categories))
        self.rules = rules or default_rules
        self.state = {
            'prev_active_window': None,
            'prev_top_windows_by_hwnd': {},
            'is_focus_app': self.is_focus_app
        }
        self.activity_log = []  # List of (timestamp, app_name, window_title)
        self.time_spent = {}    # app_name -> total seconds spent
        self.last_activity = None  # (app_name, timestamp)
        self.alerted_apps = set()
        
        # Initialize logger
        self.logger = get_logger("distraction_detector")

    def is_focus_app(self, window):
        """Return True if window is an allowed app (basic version)."""
        app_name = window.get('app_name', '').lower()
        return app_name in [a.lower() for a in self.allowed_apps]

    def update_and_detect(self, active_window, top_windows):
        """
        Run all rules and stateful checks, return list of distraction events.
        Updates state after checks.
        """
        events = []
        for rule in self.rules:
            events.extend(rule.check(active_window, top_windows, self.state))
        # Update state for next call
        self.state['prev_active_window'] = active_window
        self.state['prev_top_windows_by_hwnd'] = {w['hwnd']: w for w in top_windows if 'hwnd' in w}
        return events

    def find_distractions(self, windows: List[dict]) -> List[dict]:
        """
        Given a list of window info dicts, return a list of those that are distractions.
        Uses is_distracted() for each window.
        """
        distractions = []
        for w in windows:
            if self.is_distracted(w):
                distractions.append(w)
        return distractions

    def is_distracted(self, window_info: Dict[str, str]) -> bool:
        """
        Return True if the current window is not allowed for the task.
        Uses both app name and domain classification for browser windows.
        Never flag known system/utility processes as distractions.
        """
        app_name = window_info.get('app_name', '').lower()
        window_title = window_info.get('window_title', '')

        # Platform-specific system/utility process filter
        SYSTEM_PROCESSES = set()
        if sys.platform == "win32":
            SYSTEM_PROCESSES = {
                'systemsettings.exe',
                'taskinputhost.exe',
                'explorer.exe',
                'startmenuexperiencehost.exe',
                'searchui.exe',
                'textinputhost.exe',
                # Add more as needed
            }
        # elif sys.platform == "darwin":
        #     SYSTEM_PROCESSES = {...}  # macOS system processes
        # elif sys.platform == "linux":
        #     SYSTEM_PROCESSES = {...}  # Linux system processes

        if app_name.lower() in SYSTEM_PROCESSES:
            return False  # Never a distraction

        # Check user overrides first
        if app_name in self.user_overrides:
            return not self.user_overrides[app_name]
            
        # Check if app is in allowed list
        matches = difflib.get_close_matches(app_name, self.allowed_apps, n=1, cutoff=0.8)
        if matches:
            return False
            
        # For browser windows, check domain classification
        browsers = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe', 'safari.exe', 'opera.exe', 'brave.exe']
        if any(browser in app_name for browser in browsers) and window_title:
            # Use the browser tab tracker to determine if this is a productive tab
            self.logger.debug(f"Analyzing browser window title: {window_title}")
            
            # Get detailed information about the active tab
            active_tab_info = self.browser_tracker.get_active_tab_info()
            
            # If we have active tab info from the extension, use that instead of window title
            if active_tab_info and active_tab_info['source'] == 'extension':
                is_productive = active_tab_info['is_productive']
                domain = active_tab_info['domain']
                title = active_tab_info['title']
                url = active_tab_info['url']
                
                self.logger.debug(f"Using browser extension data for active tab: {title} ({domain})")
                
                if is_productive:
                    self.logger.debug(f"Browser tab is productive: {title} ({domain})")
                    return False
                else:
                    self.logger.debug(f"Browser tab is not productive: {title} ({domain})")
                    
                    # Special case for Zoom and other productivity tools that might be missed
                    lower_title = title.lower()
                    if any(keyword in lower_title for keyword in ['zoom', 'meet', 'teams', 'gmail', 'calendar', 'docs']):
                        self.logger.debug(f"Productivity keyword found in title, allowing: {title}")
                        return False
                        
                    return True
            else:
                # Fall back to window title parsing
                is_productive = self.browser_tracker.is_current_tab_productive(window_title)
                
                if is_productive:
                    self.logger.debug(f"Browser tab is productive: {window_title}")
                    return False
                else:
                    # Get more details about why this tab was flagged
                    tab_info = self.browser_tracker.get_tab_info().get(window_title, {})
                    domain = tab_info.get('domain')
                    
                    if domain:
                        self.logger.debug(f"Browser tab with domain {domain} is not productive")
                    else:
                        self.logger.debug(f"Browser tab without recognized domain is not productive: {window_title}")
                        
                    # Special case for Zoom and other productivity tools that might be missed
                    lower_title = window_title.lower()
                    if any(keyword in lower_title for keyword in ['zoom', 'meet', 'teams', 'gmail', 'calendar', 'docs']):
                        self.logger.debug(f"Productivity keyword found in title, allowing: {window_title}")
                        return False
                        
                    return True
        
        # Default to distracted if not explicitly allowed
        return True

    def update_activity(self, window_info: Dict[str, str]):
        """
        Update internal state with new activity info from activity monitor.
        Tracks time spent and triggers alerts if needed.
        """
        timestamp = datetime.fromisoformat(window_info["timestamp"])
        app_name = window_info["app_name"].lower()
        self.activity_log.append((timestamp, app_name, window_info.get("window_title", "")))
        # Update time spent
        if self.last_activity:
            last_app, last_time = self.last_activity
            delta = (timestamp - last_time).total_seconds()
            self.time_spent[last_app] = self.time_spent.get(last_app, 0) + max(0, delta)
        self.last_activity = (app_name, timestamp)
        # Check distraction and alert
        if self.is_distracted(window_info):
            threshold = self.distraction_thresholds.get(app_name, self.config.get('default_threshold', 60))
            spent = self.time_spent.get(app_name, 0)
            if spent >= threshold and app_name not in self.alerted_apps:
                self.trigger_alert(window_info)
                self.alerted_apps.add(app_name)
        # Log activity
        self.log_event(window_info)

    def trigger_alert(self, window_info: Dict[str, str]):
        """
        Trigger an alert for a detected distraction.
        Calls the alert callback if provided.
        """
        if self.alert_callback:
            app_name = window_info.get('app_name', 'Unknown')
            window_title = window_info.get('window_title', 'Unknown')
            message = f"Distraction detected: {app_name}\n{window_title}"
            self.alert_callback(window_info, message)
        # Log the alert
        self.logger.warning(f"Distraction detected: {window_info}")

    def log_event(self, window_info: Dict[str, str]):
        """
        Log a distraction or activity event.
        Calls the log callback if provided.
        """
        if self.log_callback:
            self.log_callback(window_info)
        # Log the activity
        self.logger.debug(f"Activity: {window_info}")

    def mark_as_allowed(self, app_name: str):
        """
        User marks an app as NOT a distraction (learning/personalization).
        """
        self.user_overrides[app_name.lower()] = True
        self.allowed_apps.add(app_name.lower())

    def mark_as_distraction(self, app_name: str):
        """
        User marks an app as a distraction (learning/personalization).
        """
        self.user_overrides[app_name.lower()] = False
        if app_name.lower() in self.allowed_apps:
            self.allowed_apps.remove(app_name.lower())

    def get_distraction_summary(self) -> List[Dict[str, Any]]:
        """
        Return a summary of all detected distractions with timestamps and context.
        """
        distractions = []
        for (timestamp, app_name, window_title) in self.activity_log:
            if app_name not in self.allowed_apps and not self.user_overrides.get(app_name, False):
                distractions.append({
                    "timestamp": timestamp,
                    "app_name": app_name,
                    "window_title": window_title
                })
        return distractions

    def configure(self, config: Dict[str, Any]):
        """
        Update configuration (allowed apps, thresholds, etc.) at runtime.
        """
        self.config.update(config)
        if 'allowed_apps' in config:
            self.allowed_apps = set(config['allowed_apps'])
        if 'distraction_thresholds' in config:
            self.distraction_thresholds = config['distraction_thresholds']
