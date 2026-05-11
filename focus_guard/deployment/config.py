"""
Deployment configuration for Focus Guard Activity Monitor.

This module defines the configuration schema for deploying the activity monitor
as a background service on a user's machine with email reporting.
"""

import os
import json
import socket
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path
from enum import Enum


class ReportFrequency(Enum):
    """Frequency options for email reports."""
    HOURLY = "hourly"
    EVERY_2_HOURS = "every_2_hours"
    EVERY_4_HOURS = "every_4_hours"
    DAILY = "daily"
    WEEKLY = "weekly"


class EnforcementMode(Enum):
    """Enforcement mode for blocking behavior.
    
    - TRACKING:  Log all activity and classifications. No blocking. No popups. Silent.
    - ADVISORY:  Log + show non-blocking notifications when budget thresholds are hit.
    - ENFORCING: Full blocking + budgets + overrides (default, current behavior).
    """
    TRACKING = "tracking"
    ADVISORY = "advisory"
    ENFORCING = "enforcing"


@dataclass
class EmailConfig:
    """Email configuration for sending reports."""
    enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""  # App password for Gmail
    use_tls: bool = True
    sender_email: str = ""
    sender_name: str = "FocusGuard Monitor"
    recipients: List[str] = field(default_factory=list)
    
    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(
            self.smtp_server and
            self.smtp_username and
            self.smtp_password and
            self.sender_email and
            self.recipients
        )


@dataclass
class ScheduleConfig:
    """Configuration for report scheduling times."""
    # Hourly report settings
    hourly_enabled: bool = True
    hourly_interval_hours: int = 1  # Deprecated: prefer hourly_interval_minutes
    hourly_interval_minutes: int = 5  # Send every N minutes (use 5 for testing)
    hourly_minute: int = 5  # Minute of the hour to send (0-59)
    
    # Daily report settings
    daily_enabled: bool = True
    daily_hour: int = 7  # Hour of day to send daily report (0-23)
    daily_minute: int = 0  # Minute of the hour to send
    
    # Weekly report settings
    weekly_enabled: bool = False
    weekly_day: int = 0  # Day of week (0=Monday, 6=Sunday)
    weekly_hour: int = 8  # Hour to send weekly report
    
    # Immediate report on service start (useful for testing)
    send_on_start: bool = False
    
    # Grace period - how many minutes after scheduled time to still send
    grace_period_minutes: int = 10

    def get_hourly_interval_minutes(self) -> int:
        """Return effective hourly report interval in minutes.

        Uses minute-level config when present, with fallback to deprecated
        hourly_interval_hours for backward compatibility.
        """
        minutes = int(self.hourly_interval_minutes or 0)
        if minutes > 0:
            return minutes

        hours = int(self.hourly_interval_hours or 1)
        if hours < 1:
            hours = 1
        return hours * 60


@dataclass
class ReportingConfig:
    """Configuration for activity reports."""
    hourly_report: bool = True  # Deprecated, use schedule.hourly_enabled
    daily_report: bool = True   # Deprecated, use schedule.daily_enabled
    weekly_report: bool = False # Deprecated, use schedule.weekly_enabled
    report_frequency: str = "hourly"  # Deprecated, use schedule.hourly_interval_hours
    include_top_apps: int = 10
    include_top_domains: int = 10
    include_hourly_breakdown: bool = True
    include_idle_stats: bool = True
    
    # New schedule configuration
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)


@dataclass
class StorageConfig:
    """Configuration for log and data storage."""
    # Base directory for all data (admin-protected)
    data_directory: str = ""
    
    # Log file settings
    log_retention_days: int = 30
    database_retention_days: int = 90
    
    # Backup settings
    backup_enabled: bool = False
    backup_directory: str = ""
    
    def get_data_directory(self) -> Path:
        """Get the data directory path, creating if needed."""
        if self.data_directory:
            path = Path(self.data_directory)
        else:
            # Default to ProgramData for admin-protected storage
            program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
            path = Path(program_data) / 'FocusGuard'
        
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class MonitoringConfig:
    """Configuration for activity monitoring behavior."""
    sampling_interval: int = 5  # seconds
    idle_threshold_short: int = 30  # seconds
    idle_threshold_medium: int = 120  # seconds
    idle_threshold_long: int = 300  # seconds
    
    # Sleep when user not logged in
    pause_when_locked: bool = True
    pause_when_screensaver: bool = True
    
    # What to monitor
    track_applications: bool = True
    track_window_titles: bool = True
    track_idle_time: bool = True
    track_browser_urls: bool = True  # Requires extension


@dataclass
class PopupConfig:
    """Configuration for personalized blocking page popups."""
    # User display name shown on the blocking page
    user_display_name: str = ""
    
    # Motivational messages rotated on the blocking page
    motivational_messages: List[str] = field(default_factory=lambda: [
        "Stay focused! You're doing great.",
        "Remember why you started. Keep going!",
        "Small steps lead to big achievements.",
        "Your future self will thank you for staying on track.",
        "Discipline is choosing between what you want now and what you want most.",
        "Every moment of focus is an investment in yourself.",
        "You don't have to be perfect, just consistent.",
        "The secret of getting ahead is getting started.",
    ])
    
    # Show streak info on the blocking page
    show_streak: bool = True
    
    # Show daily focus score
    show_focus_score: bool = True
    
    # Show motivational quotes
    show_motivational_message: bool = True
    
    # Tone: 'encouraging', 'firm', 'playful'
    tone: str = "encouraging"


@dataclass
class DeploymentConfig:
    """
    Main deployment configuration for Focus Guard Activity Monitor.
    
    This configuration is used when deploying the monitor as a service
    on another user's machine (e.g., parental monitoring).
    """
    # Machine identification
    machine_name: str = ""
    user_name: str = ""
    
    # Sub-configurations
    email: EmailConfig = field(default_factory=EmailConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    popup: PopupConfig = field(default_factory=PopupConfig)
    
    # Enforcement mode
    enforcement_mode: str = "enforcing"  # tracking | advisory | enforcing

    # Browser tab-server contract (shared by runtime and admin gateway)
    tab_server_host: str = "127.0.0.1"
    tab_server_port: int = 58392
    
    # Service settings
    run_at_startup: bool = True
    run_as_service: bool = True
    hide_from_user: bool = False  # If True, runs completely hidden

    # Day 9 install posture metadata (explicit operator model)
    deployment_posture_model: str = "admin_install_designated_monitored_user"
    installer_account_name: str = ""
    monitored_user_name: str = ""
    session_scope: str = "single_interactive_session"
    
    # Security
    require_admin_to_stop: bool = True
    config_password_hash: str = ""  # SHA256 hash of config password

    # First-run / settings wizard: remember optional UI choices
    wizard_extension_acknowledged: bool = False  # "I installed … extension" checkbox
    
    def __post_init__(self):
        """Set defaults after initialization."""
        if not self.machine_name:
            self.machine_name = socket.gethostname()
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the deployment config file."""
        program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
        return Path(program_data) / 'FocusGuard' / 'deployment_config.json'
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'DeploymentConfig':
        """
        Load configuration from file.
        
        Args:
            config_path: Path to config file, or None for default location
            
        Returns:
            DeploymentConfig instance
        """
        if config_path is None:
            config_path = cls.get_config_path()
        
        if not config_path.exists():
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct nested dataclasses
            email_data = data.get('email', {})
            # Normalize recipients to list (support comma-separated string from UI/JSON)
            recipients = email_data.get('recipients', [])
            if isinstance(recipients, str):
                recipients = [r.strip() for r in recipients.split(',') if r.strip()]
            elif not isinstance(recipients, list):
                recipients = []
            email_data['recipients'] = recipients
            email = EmailConfig(**email_data)
            
            # Handle nested ScheduleConfig in ReportingConfig
            reporting_data = data.get('reporting', {})
            schedule_data = reporting_data.pop('schedule', {}) if 'schedule' in reporting_data else {}
            if 'hourly_interval_minutes' not in schedule_data and 'hourly_interval_hours' in schedule_data:
                try:
                    schedule_data['hourly_interval_minutes'] = max(
                        1,
                        int(schedule_data.get('hourly_interval_hours', 1)) * 60,
                    )
                except Exception:
                    schedule_data['hourly_interval_minutes'] = 60
            schedule = ScheduleConfig(**schedule_data)
            reporting = ReportingConfig(**reporting_data, schedule=schedule)
            
            storage = StorageConfig(**data.get('storage', {}))
            monitoring = MonitoringConfig(**data.get('monitoring', {}))
            popup = PopupConfig(**data.get('popup', {}))
            
            return cls(
                machine_name=data.get('machine_name', ''),
                user_name=data.get('user_name', ''),
                email=email,
                reporting=reporting,
                storage=storage,
                monitoring=monitoring,
                popup=popup,
                enforcement_mode=data.get('enforcement_mode', 'enforcing'),
                tab_server_host=data.get('tab_server_host', '127.0.0.1'),
                tab_server_port=data.get('tab_server_port', 58392),
                run_at_startup=data.get('run_at_startup', True),
                run_as_service=data.get('run_as_service', True),
                hide_from_user=data.get('hide_from_user', False),
                deployment_posture_model=data.get('deployment_posture_model', 'admin_install_designated_monitored_user'),
                installer_account_name=data.get('installer_account_name', ''),
                monitored_user_name=data.get('monitored_user_name', ''),
                session_scope=data.get('session_scope', 'single_interactive_session'),
                require_admin_to_stop=data.get('require_admin_to_stop', True),
                config_password_hash=data.get('config_password_hash', ''),
                wizard_extension_acknowledged=data.get('wizard_extension_acknowledged', False),
            )
        except Exception as e:
            print(f"Error loading config: {e}")
            return cls()
    
    def save(self, config_path: Optional[Path] = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save config, or None for default location
            
        Returns:
            True if saved successfully
        """
        if config_path is None:
            config_path = self.get_config_path()
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'machine_name': self.machine_name,
                'user_name': self.user_name,
                'email': asdict(self.email),
                'reporting': asdict(self.reporting),
                'storage': asdict(self.storage),
                'monitoring': asdict(self.monitoring),
                'popup': asdict(self.popup),
                'enforcement_mode': self.enforcement_mode,
                'tab_server_host': self.tab_server_host,
                'tab_server_port': self.tab_server_port,
                'run_at_startup': self.run_at_startup,
                'run_as_service': self.run_as_service,
                'hide_from_user': self.hide_from_user,
                'deployment_posture_model': self.deployment_posture_model,
                'installer_account_name': self.installer_account_name,
                'monitored_user_name': self.monitored_user_name,
                'session_scope': self.session_scope,
                'require_admin_to_stop': self.require_admin_to_stop,
                'config_password_hash': self.config_password_hash,
                'wizard_extension_acknowledged': self.wizard_extension_acknowledged,
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate the configuration.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not self.machine_name:
            errors.append("Machine name is required")
        
        if self.email.enabled and not self.email.is_configured():
            errors.append("Email is enabled but not properly configured")
        
        if self.monitoring.sampling_interval < 1:
            errors.append("Sampling interval must be at least 1 second")
        
        if self.storage.log_retention_days < 1:
            errors.append("Log retention must be at least 1 day")
        
        valid_modes = {m.value for m in EnforcementMode}
        if self.enforcement_mode not in valid_modes:
            errors.append(f"enforcement_mode must be one of {valid_modes}, got '{self.enforcement_mode}'")

        valid_posture_models = {"admin_install_designated_monitored_user"}
        if self.deployment_posture_model not in valid_posture_models:
            errors.append(
                f"deployment_posture_model must be one of {valid_posture_models}, got '{self.deployment_posture_model}'"
            )

        valid_session_scopes = {"single_interactive_session", "best_effort_multi_session"}
        if self.session_scope not in valid_session_scopes:
            errors.append(
                f"session_scope must be one of {valid_session_scopes}, got '{self.session_scope}'"
            )
        
        return len(errors) == 0, errors
    
    def get_enforcement_mode(self) -> EnforcementMode:
        """Get the current enforcement mode as an enum."""
        try:
            return EnforcementMode(self.enforcement_mode)
        except ValueError:
            return EnforcementMode.ENFORCING


def create_default_config() -> DeploymentConfig:
    """Create a default deployment configuration."""
    return DeploymentConfig(
        machine_name=socket.gethostname(),
        user_name="",
        email=EmailConfig(
            enabled=True,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            use_tls=True
        ),
        reporting=ReportingConfig(
            hourly_report=True,
            daily_report=True,
            report_frequency="hourly"
        ),
        storage=StorageConfig(
            log_retention_days=30,
            database_retention_days=90
        ),
        monitoring=MonitoringConfig(
            sampling_interval=5,
            pause_when_locked=True
        )
    )
