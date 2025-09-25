"""
Distraction detector component for the Focus Guard coordinator.

This module provides a wrapper for the distraction detection system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.distraction.detector import DistractionDetector
from focus_guard.core.distraction.types import AlertLevel
from focus_guard.core.classification.models import Category

# Import models at runtime to avoid circular imports
from focus_guard.core.distraction.models import DistractionEvent, FocusSession, DistractionAlert


def create_distraction_component(event_bus: EventBus, config_manager: ConfigurationManager) -> Component:
    """
    Create and configure the distraction detector component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        
    Returns:
        Component: The configured distraction detector component
    """
    from focus_guard.core.distraction.detector import StandardDistractionDetector
    
    # Create the distraction detector with default settings
    distraction_detector = StandardDistractionDetector(config_manager)
    
    # Create and return the component
    return DistractionDetectorComponent(
        distraction_detector=distraction_detector,
        event_bus=event_bus,
        config_manager=config_manager
    )


class DistractionDetectedEventData(EventData):
    """Event data for distraction detected events."""
    
    def __init__(self, source: str, distraction_event: DistractionEvent):
        """
        Initialize the distraction detected event data.
        
        Args:
            source (str): The source of the event.
            distraction_event (DistractionEvent): The distraction event.
        """
        super().__init__(source)
        self.distraction_event = distraction_event
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["distraction_event"] = self.distraction_event.to_dict() if hasattr(self.distraction_event, "to_dict") else str(self.distraction_event)
        return data


class DistractionResolvedEventData(EventData):
    """Event data for distraction resolved events."""
    
    def __init__(self, source: str, distraction_event: DistractionEvent, resolution_type: str):
        """
        Initialize the distraction resolved event data.
        
        Args:
            source (str): The source of the event.
            distraction_event (DistractionEvent): The distraction event that was resolved.
            resolution_type (str): The type of resolution (e.g., "manual", "timeout", "system").
        """
        super().__init__(source)
        self.distraction_event = distraction_event
        self.resolution_type = resolution_type
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["distraction_event"] = self.distraction_event.to_dict() if hasattr(self.distraction_event, "to_dict") else str(self.distraction_event)
        data["resolution_type"] = self.resolution_type
        return data


class FocusSessionEventData(EventData):
    """Event data for focus session events."""
    
    def __init__(self, source: str, session: FocusSession, event_type: str):
        """
        Initialize the focus session event data.
        
        Args:
            source (str): The source of the event.
            session (FocusSession): The focus session.
            event_type (str): The type of session event (started, updated, ended).
        """
        super().__init__(source)
        self.session = session
        self.session_event_type = event_type
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["session"] = self.session.to_dict() if hasattr(self.session, "to_dict") else str(self.session)
        data["session_event_type"] = self.session_event_type
        return data


class DistractionDetectorComponent(BaseComponent):
    """
    Component wrapper for the distraction detection system.
    
    This component provides access to the distraction detection system and
    handles distraction events.
    """
    
    def __init__(self, distraction_detector: DistractionDetector, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the distraction detector component.
        
        Args:
            distraction_detector (DistractionDetector): The distraction detector to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("distraction_detector", event_bus, config_manager)
        self._distraction_detector = distraction_detector
        self._current_focus_session = None
        self._active_distractions = {}  # Dictionary of active distractions by domain
        self._enabled = True
        self._idle_timeout_seconds = 300  # Default idle timeout in seconds
        self._is_idle = False
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the distraction detector component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings
            self._enabled = self._config_manager.get_value(
                "distraction_detector.enabled", 
                self._enabled
            )
            self._idle_timeout_seconds = self._config_manager.get_value(
                "distraction_detector.idle_timeout_seconds", 
                self._idle_timeout_seconds
            )
            
            # Initialize the distraction detector
            self._logger.info("Initializing distraction detector")
            
            # Subscribe to relevant events
            self._event_bus.subscribe(EventTypes.DOMAIN_CLASSIFIED, self)
            self._event_bus.subscribe(EventTypes.TAB_CLOSED, self)
            self._event_bus.subscribe(EventTypes.IDLE_STATE_CHANGED, self)
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing distraction detector: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the distraction detector component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            self._logger.info("Distraction detector started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting distraction detector: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the distraction detector component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            # End current focus session if any
            if self._current_focus_session:
                await self._end_focus_session()
            
            self._logger.info("Distraction detector stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping distraction detector: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the distraction detector component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        # Nothing additional to do here
        return True
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "enabled": self._enabled,
            "active_distractions": len(self._active_distractions),
            "has_focus_session": self._current_focus_session is not None,
            "is_idle": self._is_idle
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Distraction detector is always healthy if initialized
        return True
    
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """
        Handle an event.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        await super().on_event(event_type, event_data)
        
        if not self._enabled:
            return
        
        if self._is_idle and event_type != EventTypes.IDLE_STATE_CHANGED:
            # Ignore events while idle
            return
        
        if event_type == EventTypes.DOMAIN_CLASSIFIED:
            # Check if domain is a distraction
            await self._check_for_distraction(
                event_data.domain, 
                event_data.url, 
                event_data.result.category
            )
        
        elif event_type == EventTypes.TAB_CLOSED:
            # Check if a distraction was closed
            tab = event_data.tab
            domain = self._extract_domain_from_url(tab.url)
            if domain in self._active_distractions:
                # Remove from active distractions
                distraction = self._active_distractions.pop(domain)
                self._logger.info(f"Distraction ended: {domain} (tab closed)")
                
                # Update focus session if needed
                if self._current_focus_session:
                    self._current_focus_session.add_distraction_duration(
                        domain, 
                        (datetime.now() - distraction["start_time"]).total_seconds()
                    )
                    await self._update_focus_session()
        
        elif event_type == EventTypes.IDLE_STATE_CHANGED:
            # Handle idle state changes
            self._is_idle = event_data.is_idle
            
            if self._is_idle:
                # User is idle, pause distraction tracking
                self._logger.info("User is idle, pausing distraction tracking")
                
                # Record distraction durations up to now
                now = datetime.now()
                for domain, distraction in self._active_distractions.items():
                    if self._current_focus_session:
                        self._current_focus_session.add_distraction_duration(
                            domain, 
                            (now - distraction["start_time"]).total_seconds()
                        )
                
                # Update focus session if needed
                if self._current_focus_session:
                    await self._update_focus_session()
            else:
                # User is active again, resume distraction tracking
                self._logger.info("User is active again, resuming distraction tracking")
                
                # Update start times for active distractions
                now = datetime.now()
                for domain in self._active_distractions:
                    self._active_distractions[domain]["start_time"] = now
    
    async def _check_for_distraction(self, domain: str, url: str, category: Category) -> None:
        """
        Check if a domain is a distraction and handle it accordingly.
        
        Args:
            domain (str): The domain to check.
            url (str): The URL to check.
            category (Category): The category of the domain.
        """
        try:
            # Check if this is a distraction based on the current state
            # We need to update the detector with this domain info first
            window_info = {
                'title': f'{domain} - {category.value}',
                'process_name': 'browser',
                'url': url
            }
            
            # Update the detector with current state
            self._distraction_detector.update(window_info, [window_info])
            
            # Check if we're currently distracted
            is_distraction = self._distraction_detector.is_distracted
            
            if is_distraction:
                # This is a distraction
                if domain not in self._active_distractions:
                    # New distraction
                    self._logger.info(f"Distraction detected: {domain}")
                    
                    # Create distraction event
                    distraction_event = DistractionEvent(
                        alert=DistractionAlert(
                            rule_name="domain_classification",
                            level=AlertLevel.MEDIUM,
                            message=f"Distraction detected: {domain}",
                            timestamp=datetime.now()
                        ),
                        state=None
                    )
                    
                    # Add to active distractions
                    self._active_distractions[domain] = {
                        "event": distraction_event,
                        "start_time": datetime.now()
                    }
                    
                    # Publish distraction detected event
                    await self._event_bus.publish(
                        EventTypes.DISTRACTION_DETECTED,
                        DistractionDetectedEventData("distraction_detector", distraction_event)
                    )
                    
                    # Start or update focus session
                    await self._handle_focus_session(distraction_event)
            else:
                # Not a distraction, check if it was previously a distraction
                if domain in self._active_distractions:
                    # No longer a distraction
                    distraction = self._active_distractions.pop(domain)
                    self._logger.info(f"Distraction ended: {domain} (no longer a distraction)")
                    
                    # Update focus session if needed
                    if self._current_focus_session:
                        self._current_focus_session.add_distraction_duration(
                            domain, 
                            (datetime.now() - distraction["start_time"]).total_seconds()
                        )
                        await self._update_focus_session()
        
        except Exception as e:
            self._logger.exception(f"Error checking for distraction: {e}")
    
    async def _handle_focus_session(self, distraction_event: DistractionEvent) -> None:
        """
        Handle a focus session based on a distraction event.
        
        Args:
            distraction_event (DistractionEvent): The distraction event.
        """
        # Check if we need to start a new focus session
        if not self._current_focus_session:
            await self._start_focus_session()
        else:
            # Update existing focus session
            self._current_focus_session.add_distraction(distraction_event)
            await self._update_focus_session()
    
    async def _start_focus_session(self) -> None:
        """Start a new focus session."""
        self._current_focus_session = FocusSession(
            start_time=datetime.now(),
            end_time=None,
            distractions=[],
            distraction_durations={}
        )
        
        self._logger.info("Focus session started")
        
        # Publish focus session started event
        await self._event_bus.publish(
            EventTypes.FOCUS_SESSION_STARTED,
            FocusSessionEventData("distraction_detector", self._current_focus_session, "started")
        )
    
    async def _update_focus_session(self) -> None:
        """Update the current focus session."""
        if not self._current_focus_session:
            return
        
        # Publish focus session updated event
        await self._event_bus.publish(
            EventTypes.FOCUS_SESSION_UPDATED,
            FocusSessionEventData("distraction_detector", self._current_focus_session, "updated")
        )
    
    async def _end_focus_session(self) -> None:
        """End the current focus session."""
        if not self._current_focus_session:
            return
        
        # Set end time
        self._current_focus_session.end_time = datetime.now()
        
        # Add final distraction durations
        now = datetime.now()
        for domain, distraction in self._active_distractions.items():
            self._current_focus_session.add_distraction_duration(
                domain, 
                (now - distraction["start_time"]).total_seconds()
            )
        
        # Publish focus session ended event
        await self._event_bus.publish(
            EventTypes.FOCUS_SESSION_ENDED,
            FocusSessionEventData("distraction_detector", self._current_focus_session, "ended")
        )
        
        self._logger.info("Focus session ended")
        
        # Clear current focus session
        self._current_focus_session = None
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "distraction_detector.enabled":
            old_enabled = self._enabled
            self._enabled = new_value
            
            self._logger.info(f"Distraction detector {'enabled' if new_value else 'disabled'}")
            
            if old_enabled and not new_value:
                # Detector was disabled, end current focus session if any
                if self._current_focus_session:
                    await self._end_focus_session()
                
                # Clear active distractions
                self._active_distractions = {}
        
        elif path == "distraction_detector.idle_timeout_seconds":
            self._idle_timeout_seconds = new_value
            self._logger.info(f"Updated idle timeout to {new_value} seconds")
    
    def get_distraction_detector(self) -> DistractionDetector:
        """
        Get the distraction detector.
        
        Returns:
            DistractionDetector: The distraction detector.
        """
        return self._distraction_detector
    
    def get_current_focus_session(self) -> Optional[FocusSession]:
        """
        Get the current focus session.
        
        Returns:
            Optional[FocusSession]: The current focus session, or None if no session is active.
        """
        return self._current_focus_session
    
    def get_active_distractions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the active distractions.
        
        Returns:
            Dict[str, Dict[str, Any]]: A dictionary of active distractions by domain.
        """
        return self._active_distractions
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # The component is healthy if the distraction detector is available
        return self._distraction_detector is not None
    
    def _extract_domain_from_url(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url (str): The URL to extract the domain from.
            
        Returns:
            str: The domain.
        """
        if not url:
            return ""
        
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            return parsed_url.netloc
        except Exception:
            return ""
