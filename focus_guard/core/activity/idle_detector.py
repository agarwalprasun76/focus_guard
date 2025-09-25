"""
Comprehensive idle detection system for accurate active usage tracking.

This module provides cross-platform idle detection with configurable thresholds,
idle state tracking, and integration with the activity monitoring system.
"""

import time
import threading
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import sys
import logging

logger = logging.getLogger(__name__)


class IdleState(Enum):
    """Enumeration of possible idle states."""
    ACTIVE = "active"
    SHORT_IDLE = "short_idle"  # 1-5 minutes
    MEDIUM_IDLE = "medium_idle"  # 5-15 minutes
    LONG_IDLE = "long_idle"  # 15+ minutes


@dataclass
class IdleEvent:
    """Represents an idle state change event."""
    timestamp: datetime
    previous_state: IdleState
    current_state: IdleState
    idle_duration: float  # seconds
    active_duration: float  # seconds since last active


@dataclass
class IdleConfiguration:
    """Configuration for idle detection thresholds."""
    short_idle_threshold: float = 60.0  # 1 minute
    medium_idle_threshold: float = 300.0  # 5 minutes
    long_idle_threshold: float = 900.0  # 15 minutes
    polling_interval: float = 5.0  # Check every 5 seconds
    sensitivity: float = 1.0  # Multiplier for thresholds


class PlatformIdleDetector:
    """Base class for platform-specific idle detection."""
    
    def get_idle_time_seconds(self) -> float:
        """Get system idle time in seconds."""
        raise NotImplementedError
    
    def is_supported(self) -> bool:
        """Check if this detector is supported on current platform."""
        raise NotImplementedError


class WindowsIdleDetector(PlatformIdleDetector):
    """Windows-specific idle detection using GetLastInputInfo."""
    
    def get_idle_time_seconds(self) -> float:
        """Get Windows system idle time in seconds."""
        try:
            import ctypes
            
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint),
                ]
            
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
            
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return max(0.0, millis / 1000.0)
            else:
                return 0.0
        except Exception as e:
            logger.warning(f"Failed to get Windows idle time: {e}")
            return 0.0
    
    def is_supported(self) -> bool:
        """Check if Windows idle detection is supported."""
        return sys.platform == "win32"


class LinuxIdleDetector(PlatformIdleDetector):
    """Linux-specific idle detection using X11."""
    
    def get_idle_time_seconds(self) -> float:
        """Get Linux system idle time in seconds."""
        try:
            # Try xprintidle first (most accurate)
            import subprocess
            result = subprocess.run(['xprintidle'], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                return float(result.stdout.strip()) / 1000.0
        except Exception:
            pass
        
        try:
            # Fallback to xssstate
            import subprocess
            result = subprocess.run(['xssstate', '-i'], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                return float(result.stdout.strip()) / 1000.0
        except Exception:
            pass
        
        try:
            # Fallback to parsing /proc/interrupts (less accurate)
            with open('/proc/interrupts', 'r') as f:
                lines = f.readlines()
                # This is a simplified approach - real implementation would be more complex
                return 0.0
        except Exception as e:
            logger.warning(f"Failed to get Linux idle time: {e}")
            return 0.0
    
    def is_supported(self) -> bool:
        """Check if Linux idle detection is supported."""
        return sys.platform.startswith("linux")


class MacOSIdleDetector(PlatformIdleDetector):
    """macOS-specific idle detection using Core Graphics."""
    
    def get_idle_time_seconds(self) -> float:
        """Get macOS system idle time in seconds."""
        try:
            from Quartz import CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
            return CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
        except Exception as e:
            logger.warning(f"Failed to get macOS idle time: {e}")
            return 0.0
    
    def is_supported(self) -> bool:
        """Check if macOS idle detection is supported."""
        if sys.platform != "darwin":
            return False
        try:
            import Quartz
            return True
        except ImportError:
            return False


class IdleDetector:
    """
    Comprehensive idle detection system with state tracking and callbacks.
    
    This class provides:
    - Cross-platform idle time detection
    - Configurable idle state thresholds
    - State change callbacks
    - Idle period tracking
    - Active usage filtering
    """
    
    def __init__(self, config: Optional[IdleConfiguration] = None):
        """
        Initialize the idle detector.
        
        Args:
            config: Configuration for idle detection thresholds
        """
        self.config = config or IdleConfiguration()
        self.platform_detector = self._get_platform_detector()
        
        # State tracking
        self.current_state = IdleState.ACTIVE
        self.last_state_change = datetime.now()
        self.last_activity_time = datetime.now()
        self.idle_start_time: Optional[datetime] = None
        
        # Callbacks
        self.state_change_callbacks: List[Callable[[IdleEvent], None]] = []
        
        # Threading
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Statistics
        self.total_active_time = 0.0
        self.total_idle_time = 0.0
        self.idle_periods: List[Dict[str, Any]] = []
        
    def _get_platform_detector(self) -> PlatformIdleDetector:
        """Get the appropriate platform-specific idle detector."""
        detectors = [
            WindowsIdleDetector(),
            LinuxIdleDetector(),
            MacOSIdleDetector()
        ]
        
        for detector in detectors:
            if detector.is_supported():
                logger.info(f"Using {detector.__class__.__name__} for idle detection")
                return detector
        
        logger.warning("No supported idle detector found, using fallback")
        return WindowsIdleDetector()  # Fallback
    
    def get_idle_time_seconds(self) -> float:
        """Get current system idle time in seconds."""
        return self.platform_detector.get_idle_time_seconds()
    
    def get_current_state(self) -> IdleState:
        """Get the current idle state."""
        with self._lock:
            return self.current_state
    
    def is_idle(self, threshold_seconds: float = None) -> bool:
        """
        Check if system is currently idle.
        
        Args:
            threshold_seconds: Custom threshold, or use short_idle_threshold if None
            
        Returns:
            bool: True if system is idle beyond threshold
        """
        if threshold_seconds is None:
            threshold_seconds = self.config.short_idle_threshold
        
        return self.get_idle_time_seconds() >= threshold_seconds
    
    def is_active(self) -> bool:
        """Check if system is currently active (not idle)."""
        return not self.is_idle()
    
    def add_state_change_callback(self, callback: Callable[[IdleEvent], None]):
        """Add a callback to be called when idle state changes."""
        self.state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[IdleEvent], None]):
        """Remove a state change callback."""
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)
    
    def start_monitoring(self):
        """Start continuous idle state monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Idle monitoring started")
    
    def stop_monitoring(self):
        """Stop idle state monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        logger.info("Idle monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        while self._monitoring:
            try:
                self._update_idle_state()
                time.sleep(self.config.polling_interval)
            except Exception as e:
                logger.error(f"Error in idle monitoring loop: {e}")
                time.sleep(self.config.polling_interval)
    
    def _update_idle_state(self):
        """Update the current idle state based on system idle time."""
        idle_time = self.get_idle_time_seconds()
        now = datetime.now()
        
        # Apply sensitivity multiplier
        adjusted_thresholds = {
            'short': self.config.short_idle_threshold * self.config.sensitivity,
            'medium': self.config.medium_idle_threshold * self.config.sensitivity,
            'long': self.config.long_idle_threshold * self.config.sensitivity
        }
        
        # Determine new state
        if idle_time < adjusted_thresholds['short']:
            new_state = IdleState.ACTIVE
        elif idle_time < adjusted_thresholds['medium']:
            new_state = IdleState.SHORT_IDLE
        elif idle_time < adjusted_thresholds['long']:
            new_state = IdleState.MEDIUM_IDLE
        else:
            new_state = IdleState.LONG_IDLE
        
        with self._lock:
            if new_state != self.current_state:
                self._handle_state_change(new_state, idle_time, now)
    
    def _handle_state_change(self, new_state: IdleState, idle_time: float, timestamp: datetime):
        """Handle idle state change and update statistics."""
        previous_state = self.current_state
        state_duration = (timestamp - self.last_state_change).total_seconds()
        
        # Update statistics
        if previous_state == IdleState.ACTIVE:
            self.total_active_time += state_duration
            if new_state != IdleState.ACTIVE:
                self.idle_start_time = timestamp
        else:
            self.total_idle_time += state_duration
            if new_state == IdleState.ACTIVE:
                # End of idle period
                if self.idle_start_time:
                    idle_period = {
                        'start_time': self.idle_start_time,
                        'end_time': timestamp,
                        'duration': (timestamp - self.idle_start_time).total_seconds(),
                        'max_state': previous_state.value
                    }
                    self.idle_periods.append(idle_period)
                    self.idle_start_time = None
                self.last_activity_time = timestamp
        
        # Create event
        active_duration = (timestamp - self.last_activity_time).total_seconds()
        event = IdleEvent(
            timestamp=timestamp,
            previous_state=previous_state,
            current_state=new_state,
            idle_duration=idle_time,
            active_duration=active_duration
        )
        
        # Update state
        self.current_state = new_state
        self.last_state_change = timestamp
        
        logger.debug(f"Idle state changed: {previous_state.value} -> {new_state.value} "
                    f"(idle: {idle_time:.1f}s, active: {active_duration:.1f}s)")
        
        # Notify callbacks
        for callback in self.state_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in idle state callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get idle detection statistics."""
        with self._lock:
            total_time = self.total_active_time + self.total_idle_time
            return {
                'current_state': self.current_state.value,
                'current_idle_time': self.get_idle_time_seconds(),
                'total_active_time': self.total_active_time,
                'total_idle_time': self.total_idle_time,
                'active_percentage': (self.total_active_time / total_time * 100) if total_time > 0 else 0,
                'idle_periods_count': len(self.idle_periods),
                'last_activity_time': self.last_activity_time.isoformat(),
                'monitoring': self._monitoring,
                'platform_detector': self.platform_detector.__class__.__name__
            }
    
    def get_recent_idle_periods(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get idle periods from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            period for period in self.idle_periods
            if period['start_time'] >= cutoff_time
        ]
    
    def reset_statistics(self):
        """Reset all statistics and idle period tracking."""
        with self._lock:
            self.total_active_time = 0.0
            self.total_idle_time = 0.0
            self.idle_periods.clear()
            self.last_activity_time = datetime.now()
            logger.info("Idle detection statistics reset")
