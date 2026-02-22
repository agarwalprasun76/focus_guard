"""Browser extension installer package.

Provides strategies and orchestration for installing the Focus Guard
browser extension across different browsers and deployment scenarios.
"""

from .strategies import (
    InstallerStrategy,
    InstallResult,
    InstallStatus,
    BrowserInfo,
    DevUnpackedStrategy,
    StoreInstallStrategy,
    EnterpriseStrategy,
    detect_browsers,
    get_default_strategy,
)
from .core_installer import (
    ExtensionInstaller,
    InstallMode,
    InstallationStatus,
    install_extension,
    get_extension_status,
)

__all__ = [
    # Strategies
    "InstallerStrategy",
    "InstallResult",
    "InstallStatus",
    "BrowserInfo",
    "DevUnpackedStrategy",
    "StoreInstallStrategy",
    "EnterpriseStrategy",
    "detect_browsers",
    "get_default_strategy",
    # Core installer
    "ExtensionInstaller",
    "InstallMode",
    "InstallationStatus",
    "install_extension",
    "get_extension_status",
]
