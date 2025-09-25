"""
Alert providers package.

This package contains implementations of various alert providers that can be used
to send alerts through different channels (popup, sound, email, etc.).
"""

from focus_guard.core.alert.providers.base import (
    AlertProvider,
    CompositeAlertProvider,
    ConditionalAlertProvider
)
from focus_guard.core.alert.providers.popup import PopupAlertProvider
from focus_guard.core.alert.providers.sound import SoundAlertProvider
from focus_guard.core.alert.providers.app import AppAlertProvider
from focus_guard.core.alert.providers.blocking import BlockingAlertProvider
from focus_guard.core.alert.providers.email import EmailAlertProvider
from focus_guard.core.alert.providers.webhook import WebhookAlertProvider
from focus_guard.core.alert.providers.standard import StandardAlertProvider

__all__ = [
    'AlertProvider',
    'CompositeAlertProvider',
    'ConditionalAlertProvider',
    'PopupAlertProvider',
    'SoundAlertProvider',
    'AppAlertProvider',
    'BlockingAlertProvider',
    'EmailAlertProvider',
    'WebhookAlertProvider',
    'StandardAlertProvider'
]
