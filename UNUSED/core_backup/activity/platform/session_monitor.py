"""
Session monitoring for Focus Guard.

This module provides functionality to detect user session events
(login, logout, lock, unlock) and trigger appropriate actions.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum, auto


class SessionEvent(Enum):
    """Enum for session event types."""
    LOGIN = auto()
    LOGOUT = auto()
    LOCK = auto()
    UNLOCK = auto()


class SessionListener(ABC):
    """Abstract base class for session event listeners."""
    
    @abstractmethod
    def on_session_event(self, event_type: SessionEvent, event_data: Dict[str, Any]) -> None:
        """
        Handle a session event.
        
        Args:
            event_type: Type of session event
            event_data: Additional data about the event
        """
        pass


class SessionMonitor(ABC):
    """Abstract base class for platform-specific session monitors."""
    
    def __init__(self):
        """Initialize the session monitor."""
        self.listeners: List[SessionListener] = []
        self.logger = logging.getLogger("session_monitor")
        self._configure_logger()
        self.running = False
        self.thread = None
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
    
    def add_listener(self, listener: SessionListener) -> None:
        """
        Add a session event listener.
        
        Args:
            listener: The listener to add
        """
        if listener not in self.listeners:
            self.listeners.append(listener)
    
    def remove_listener(self, listener: SessionListener) -> None:
        """
        Remove a session event listener.
        
        Args:
            listener: The listener to remove
        """
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    def notify_listeners(self, event_type: SessionEvent, event_data: Dict[str, Any] = None) -> None:
        """
        Notify all listeners of a session event.
        
        Args:
            event_type: Type of session event
            event_data: Additional data about the event
        """
        if event_data is None:
            event_data = {}
            
        for listener in self.listeners:
            try:
                listener.on_session_event(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Error notifying listener {listener}: {e}")
    
    def start(self) -> None:
        """Start monitoring for session events."""
        if self.running:
            self.logger.warning("Session monitor is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Session monitoring started")
    
    def stop(self) -> None:
        """Stop monitoring for session events."""
        if not self.running:
            self.logger.warning("Session monitor is not running")
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.logger.info("Session monitoring stopped")
    
    @abstractmethod
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that runs in a separate thread.
        
        This method should be implemented by platform-specific subclasses
        to detect session events and call notify_listeners.
        """
        pass
    
    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """
        Check if this session monitor implementation is supported on the current system.
        
        Returns:
            bool: True if this implementation is supported, False otherwise.
        """
        pass
