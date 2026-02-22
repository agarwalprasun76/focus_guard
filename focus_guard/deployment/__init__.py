"""
Focus Guard Deployment Module.

This module provides functionality for deploying the activity monitor
as a background service with email reporting capabilities.

Key features:
- Tamper-resistant service installation
- Email reporting (hourly/daily)
- Lightweight resource optimization
- Protected file storage
"""

from focus_guard.deployment.config import (
    DeploymentConfig,
    EmailConfig,
    ReportingConfig,
    StorageConfig,
    MonitoringConfig,
    ReportFrequency,
    create_default_config
)

from focus_guard.deployment.hardening import (
    apply_all_hardening,
    get_hardening_status,
    SECURITY_RECOMMENDATIONS
)

from focus_guard.deployment.lightweight import (
    ResourceLimits,
    LightweightMonitor,
    RESOURCE_GUIDELINES
)

__all__ = [
    # Config
    'DeploymentConfig',
    'EmailConfig',
    'ReportingConfig',
    'StorageConfig',
    'MonitoringConfig',
    'ReportFrequency',
    'create_default_config',
    # Hardening
    'apply_all_hardening',
    'get_hardening_status',
    'SECURITY_RECOMMENDATIONS',
    # Lightweight
    'ResourceLimits',
    'LightweightMonitor',
    'RESOURCE_GUIDELINES',
]
