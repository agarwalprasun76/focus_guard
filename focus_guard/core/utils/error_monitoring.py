"""
Enhanced error monitoring and alerting system for Focus Guard.

This module provides centralized error tracking, metrics collection,
and alerting capabilities for robust system monitoring.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Alert types for error monitoring."""
    ERROR_RATE_EXCEEDED = "error_rate_exceeded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    SERVICE_UNAVAILABLE = "service_unavailable"
    CLASSIFICATION_FAILURE = "classification_failure"
    SYSTEM_DEGRADED = "system_degraded"

@dataclass
class ErrorEvent:
    """Represents an error event for monitoring."""
    timestamp: float
    component: str
    error_type: str
    message: str
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None

@dataclass
class AlertEvent:
    """Represents an alert event."""
    timestamp: float
    alert_type: AlertType
    component: str
    message: str
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)

class ErrorMetrics:
    """Tracks error metrics and statistics."""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._errors = deque(maxlen=window_size)
        self._error_counts = defaultdict(int)
        self._component_errors = defaultdict(lambda: defaultdict(int))
        self._lock = threading.Lock()
    
    def record_error(self, error_event: ErrorEvent):
        """Record an error event."""
        with self._lock:
            self._errors.append(error_event)
            self._error_counts[error_event.error_type] += 1
            self._component_errors[error_event.component][error_event.error_type] += 1
    
    def get_error_rate(self, time_window: float = 300.0) -> float:
        """Get error rate per minute in the specified time window."""
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        with self._lock:
            recent_errors = [e for e in self._errors if e.timestamp >= cutoff_time]
            return len(recent_errors) / (time_window / 60.0)  # Errors per minute
    
    def get_component_error_rate(self, component: str, time_window: float = 300.0) -> float:
        """Get error rate for a specific component."""
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        with self._lock:
            component_errors = [e for e in self._errors 
                              if e.component == component and e.timestamp >= cutoff_time]
            return len(component_errors) / (time_window / 60.0)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary."""
        with self._lock:
            total_errors = len(self._errors)
            error_rate = self.get_error_rate()
            
            # Get top error types
            top_errors = sorted(self._error_counts.items(), 
                              key=lambda x: x[1], reverse=True)[:5]
            
            # Get component breakdown
            component_breakdown = {}
            for component, errors in self._component_errors.items():
                component_breakdown[component] = {
                    'total_errors': sum(errors.values()),
                    'error_rate': self.get_component_error_rate(component),
                    'top_errors': sorted(errors.items(), 
                                       key=lambda x: x[1], reverse=True)[:3]
                }
            
            return {
                'total_errors': total_errors,
                'error_rate_per_minute': error_rate,
                'top_error_types': top_errors,
                'component_breakdown': component_breakdown,
                'window_size': self.window_size,
                'timestamp': time.time()
            }

class ErrorMonitor:
    """Central error monitoring and alerting system."""
    
    def __init__(self, 
                 error_rate_threshold: float = 10.0,  # Errors per minute
                 alert_cooldown: float = 300.0):      # 5 minutes
        self.error_rate_threshold = error_rate_threshold
        self.alert_cooldown = alert_cooldown
        
        self.metrics = ErrorMetrics()
        self._alert_handlers: List[Callable[[AlertEvent], None]] = []
        self._last_alerts: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Component health tracking
        self._component_health = defaultdict(lambda: {
            'status': 'healthy',
            'last_error': None,
            'consecutive_errors': 0,
            'last_success': time.time()
        })
    
    def add_alert_handler(self, handler: Callable[[AlertEvent], None]):
        """Add an alert handler function."""
        self._alert_handlers.append(handler)
    
    def record_error(self, 
                    component: str,
                    error_type: str,
                    message: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    stack_trace: Optional[str] = None):
        """Record an error event and check for alerts."""
        error_event = ErrorEvent(
            timestamp=time.time(),
            component=component,
            error_type=error_type,
            message=message,
            severity=severity,
            context=context or {},
            stack_trace=stack_trace
        )
        
        self.metrics.record_error(error_event)
        self._update_component_health(component, error_event)
        self._check_alerts(error_event)
        
        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.WARNING)
        
        logger.log(log_level, f"[{component}] {error_type}: {message}")
    
    def record_success(self, component: str):
        """Record a successful operation for a component."""
        with self._lock:
            health = self._component_health[component]
            health['last_success'] = time.time()
            health['consecutive_errors'] = 0
            if health['status'] != 'healthy':
                health['status'] = 'healthy'
                logger.info(f"Component {component} recovered to healthy status")
    
    def _update_component_health(self, component: str, error_event: ErrorEvent):
        """Update component health status based on error."""
        with self._lock:
            health = self._component_health[component]
            health['last_error'] = error_event.timestamp
            health['consecutive_errors'] += 1
            
            # Determine health status
            if health['consecutive_errors'] >= 5:
                health['status'] = 'critical'
            elif health['consecutive_errors'] >= 3:
                health['status'] = 'degraded'
            elif error_event.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                health['status'] = 'degraded'
    
    def _check_alerts(self, error_event: ErrorEvent):
        """Check if any alerts should be triggered."""
        current_time = time.time()
        
        # Check error rate alert
        error_rate = self.metrics.get_error_rate()
        if error_rate > self.error_rate_threshold:
            self._trigger_alert(
                AlertType.ERROR_RATE_EXCEEDED,
                error_event.component,
                f"Error rate exceeded threshold: {error_rate:.1f} errors/min",
                ErrorSeverity.HIGH,
                {'error_rate': error_rate, 'threshold': self.error_rate_threshold}
            )
        
        # Check component health alerts
        with self._lock:
            health = self._component_health[error_event.component]
            if health['status'] == 'critical':
                self._trigger_alert(
                    AlertType.SERVICE_UNAVAILABLE,
                    error_event.component,
                    f"Component {error_event.component} is in critical state",
                    ErrorSeverity.CRITICAL,
                    {'consecutive_errors': health['consecutive_errors']}
                )
            elif health['status'] == 'degraded':
                self._trigger_alert(
                    AlertType.SYSTEM_DEGRADED,
                    error_event.component,
                    f"Component {error_event.component} is degraded",
                    ErrorSeverity.HIGH,
                    {'consecutive_errors': health['consecutive_errors']}
                )
        
        # Check for specific error types
        if error_event.error_type == 'classification_failure':
            self._trigger_alert(
                AlertType.CLASSIFICATION_FAILURE,
                error_event.component,
                f"Classification failure: {error_event.message}",
                error_event.severity,
                error_event.context
            )
    
    def _trigger_alert(self, 
                      alert_type: AlertType,
                      component: str,
                      message: str,
                      severity: ErrorSeverity,
                      context: Dict[str, Any]):
        """Trigger an alert if not in cooldown period."""
        alert_key = f"{alert_type.value}:{component}"
        current_time = time.time()
        
        # Check cooldown
        if alert_key in self._last_alerts:
            if current_time - self._last_alerts[alert_key] < self.alert_cooldown:
                return
        
        self._last_alerts[alert_key] = current_time
        
        alert_event = AlertEvent(
            timestamp=current_time,
            alert_type=alert_type,
            component=component,
            message=message,
            severity=severity,
            context=context
        )
        
        # Send to all alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert_event)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        with self._lock:
            component_health = dict(self._component_health)
        
        metrics_summary = self.metrics.get_error_summary()
        
        # Determine overall health
        overall_status = 'healthy'
        critical_components = []
        degraded_components = []
        
        for component, health in component_health.items():
            if health['status'] == 'critical':
                critical_components.append(component)
                overall_status = 'critical'
            elif health['status'] == 'degraded':
                degraded_components.append(component)
                if overall_status == 'healthy':
                    overall_status = 'degraded'
        
        return {
            'overall_status': overall_status,
            'component_health': component_health,
            'critical_components': critical_components,
            'degraded_components': degraded_components,
            'metrics': metrics_summary,
            'timestamp': time.time()
        }
    
    def reset_component_health(self, component: str):
        """Reset health status for a component."""
        with self._lock:
            if component in self._component_health:
                self._component_health[component] = {
                    'status': 'healthy',
                    'last_error': None,
                    'consecutive_errors': 0,
                    'last_success': time.time()
                }
                logger.info(f"Reset health status for component: {component}")

# Global error monitor instance
_global_monitor: Optional[ErrorMonitor] = None

def get_error_monitor() -> ErrorMonitor:
    """Get the global error monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ErrorMonitor()
        
        # Add default console alert handler
        def console_alert_handler(alert: AlertEvent):
            logger.warning(f"ALERT [{alert.alert_type.value}] {alert.component}: {alert.message}")
        
        _global_monitor.add_alert_handler(console_alert_handler)
    
    return _global_monitor

def record_error(component: str,
                error_type: str,
                message: str,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                context: Optional[Dict[str, Any]] = None,
                stack_trace: Optional[str] = None):
    """Convenience function to record an error."""
    monitor = get_error_monitor()
    monitor.record_error(component, error_type, message, severity, context, stack_trace)

def record_success(component: str):
    """Convenience function to record a success."""
    monitor = get_error_monitor()
    monitor.record_success(component)
