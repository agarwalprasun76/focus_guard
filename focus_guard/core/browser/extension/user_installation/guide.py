"""
Extension installation guide module.

This module provides a user-friendly guide for permanently installing
browser extensions using developer mode.
"""

import os
import logging
import webbrowser
import subprocess
from typing import Dict, Optional, List, Any
from enum import Enum, auto
from pathlib import Path

from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.extension.manager import BrowserExtensionManager

logger = logging.getLogger(__name__)


class InstallationStep(Enum):
    """Steps in the extension installation process."""
    OPEN_EXTENSIONS_PAGE = auto()
    ENABLE_DEVELOPER_MODE = auto()
    LOAD_UNPACKED = auto()
    SELECT_DIRECTORY = auto()
    VERIFY_INSTALLATION = auto()
    PIN_EXTENSION = auto()
    COMPLETE = auto()


class ExtensionInstallationGuide:
    """Guide users through permanent extension installation using developer mode."""
    
    def __init__(self, extension_dir: Optional[str] = None):
        """Initialize the installation guide.
        
        Args:
            extension_dir: Path to the extension directory. If None, will use default.
        """
        self._extension_manager = BrowserExtensionManager(extension_dir)
        self._extension_dir = extension_dir or self._extension_manager._extension_dir
        self._browser_paths = self._extension_manager._browser_paths
        
        # Store installation progress for each browser
        self._installation_progress: Dict[BrowserType, InstallationStep] = {}
        
        # Store browser-specific extension pages
        self._extension_pages = {
            BrowserType.CHROME: "chrome://extensions",
            BrowserType.EDGE: "edge://extensions",
            BrowserType.FIREFOX: "about:addons",
            BrowserType.SAFARI: "safari://extensions",
            BrowserType.BRAVE: "brave://extensions",
            BrowserType.OPERA: "opera://extensions",
            BrowserType.VIVALDI: "vivaldi://extensions",
        }
        
        # Generate browser-specific instructions
        self._instructions = self._generate_instructions()
        
    def _generate_instructions(self) -> Dict[BrowserType, Dict[InstallationStep, str]]:
        """Generate browser-specific instructions for each installation step.
        
        Returns:
            Dictionary mapping browser types to step instructions
        """
        instructions = {}
        
        # Chrome instructions
        instructions[BrowserType.CHROME] = {
            InstallationStep.OPEN_EXTENSIONS_PAGE: 
                "Opening Chrome Extensions page (chrome://extensions)...",
            InstallationStep.ENABLE_DEVELOPER_MODE: 
                "Please enable Developer Mode by toggling the switch in the top-right corner.",
            InstallationStep.LOAD_UNPACKED: 
                "Click the 'Load unpacked' button that appears after enabling Developer Mode.",
            InstallationStep.SELECT_DIRECTORY: 
                f"Select the following directory:\n{self._extension_dir}",
            InstallationStep.VERIFY_INSTALLATION: 
                "Verify that the 'Focus Guard' extension appears in your extensions list.",
            InstallationStep.PIN_EXTENSION: 
                "Click the Extensions button in the toolbar, then pin Focus Guard for easy access.",
            InstallationStep.COMPLETE: 
                "Installation complete! Focus Guard is now permanently installed in Chrome."
        }
        
        # Edge instructions (similar to Chrome)
        instructions[BrowserType.EDGE] = {
            InstallationStep.OPEN_EXTENSIONS_PAGE: 
                "Opening Edge Extensions page (edge://extensions)...",
            InstallationStep.ENABLE_DEVELOPER_MODE: 
                "Please enable Developer Mode by toggling the switch in the left sidebar.",
            InstallationStep.LOAD_UNPACKED: 
                "Click the 'Load unpacked' button that appears after enabling Developer Mode.",
            InstallationStep.SELECT_DIRECTORY: 
                f"Select the following directory:\n{self._extension_dir}",
            InstallationStep.VERIFY_INSTALLATION: 
                "Verify that the 'Focus Guard' extension appears in your extensions list.",
            InstallationStep.PIN_EXTENSION: 
                "Click the Extensions button in the toolbar, then pin Focus Guard for easy access.",
            InstallationStep.COMPLETE: 
                "Installation complete! Focus Guard is now permanently installed in Edge."
        }
        
        # Firefox instructions (different process)
        instructions[BrowserType.FIREFOX] = {
            InstallationStep.OPEN_EXTENSIONS_PAGE: 
                "Opening Firefox Add-ons page (about:addons)...",
            InstallationStep.ENABLE_DEVELOPER_MODE: 
                "Click the gear icon and select 'Debug Add-ons'.",
            InstallationStep.LOAD_UNPACKED: 
                "Click 'Load Temporary Add-on...'",
            InstallationStep.SELECT_DIRECTORY: 
                f"Navigate to {self._extension_dir} and select the manifest.json file.",
            InstallationStep.VERIFY_INSTALLATION: 
                "Verify that the 'Focus Guard' extension appears in your add-ons list.",
            InstallationStep.PIN_EXTENSION: 
                "Right-click the Focus Guard icon in the toolbar and select 'Pin to Toolbar'.",
            InstallationStep.COMPLETE: 
                "Installation complete! Note: Firefox extensions loaded this way are temporary and will be removed when Firefox is restarted."
        }
        
        # Add default instructions for other browsers
        for browser_type in BrowserType:
            if browser_type not in instructions:
                instructions[browser_type] = instructions[BrowserType.CHROME].copy()
                # Update browser-specific text
                instructions[browser_type][InstallationStep.OPEN_EXTENSIONS_PAGE] = \
                    f"Opening {browser_type.name.capitalize()} Extensions page..."
                instructions[browser_type][InstallationStep.COMPLETE] = \
                    f"Installation complete! Focus Guard is now installed in {browser_type.name.capitalize()}."
        
        return instructions
    
    def start_installation_guide(self, browser_type: BrowserType) -> bool:
        """Start the installation guide for a specific browser.
        
        Args:
            browser_type: Type of browser to install extension for
            
        Returns:
            bool: True if guide started successfully
        """
        if browser_type not in self._browser_paths:
            logger.error(f"Browser {browser_type.name} not found on system")
            return False
            
        # Reset installation progress
        self._installation_progress[browser_type] = InstallationStep.OPEN_EXTENSIONS_PAGE
        
        # Show first instruction
        self._show_instruction(browser_type, InstallationStep.OPEN_EXTENSIONS_PAGE)
        
        # Open extensions page
        return self._open_extensions_page(browser_type)
    
    def _open_extensions_page(self, browser_type: BrowserType) -> bool:
        """Open the extensions page for a browser.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            bool: True if page opened successfully
        """
        if browser_type not in self._extension_pages:
            logger.error(f"Extension page URL not defined for {browser_type.name}")
            return False
            
        browser_path = self._browser_paths.get(browser_type)
        if not browser_path:
            logger.error(f"Browser path not found for {browser_type.name}")
            return False
            
        extension_url = self._extension_pages[browser_type]
        
        try:
            # Launch browser with extensions page
            subprocess.Popen([browser_path, extension_url])
            logger.info(f"Opened {extension_url} in {browser_type.name}")
            
            # Update progress
            self._installation_progress[browser_type] = InstallationStep.ENABLE_DEVELOPER_MODE
            self._show_instruction(browser_type, InstallationStep.ENABLE_DEVELOPER_MODE)
            
            return True
        except Exception as e:
            logger.error(f"Error opening extensions page for {browser_type.name}: {e}")
            return False
    
    def advance_to_next_step(self, browser_type: BrowserType) -> bool:
        """Advance to the next installation step.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            bool: True if advanced successfully, False if already at last step
        """
        if browser_type not in self._installation_progress:
            logger.error(f"No installation in progress for {browser_type.name}")
            return False
            
        current_step = self._installation_progress[browser_type]
        
        # Get next step
        steps = list(InstallationStep)
        current_index = steps.index(current_step)
        
        if current_index >= len(steps) - 1:
            logger.info(f"Already at last step for {browser_type.name}")
            return False
            
        next_step = steps[current_index + 1]
        self._installation_progress[browser_type] = next_step
        
        # Show instruction for next step
        self._show_instruction(browser_type, next_step)
        
        return True
    
    def _show_instruction(self, browser_type: BrowserType, step: InstallationStep) -> None:
        """Show instruction for a specific step.
        
        Args:
            browser_type: Type of browser
            step: Installation step
        """
        if browser_type not in self._instructions or step not in self._instructions[browser_type]:
            logger.error(f"No instruction found for {browser_type.name} at step {step.name}")
            return
            
        instruction = self._instructions[browser_type][step]
        
        # In a real application, this would show a GUI dialog
        # For now, we'll just log the instruction
        logger.info(f"[{browser_type.name}] [{step.name}] {instruction}")
        
        # TODO: Replace with actual GUI dialog in the future
        print(f"\n=== {browser_type.name} EXTENSION INSTALLATION - STEP {list(InstallationStep).index(step) + 1} ===")
        print(instruction)
        print("=" * 60)
    
    def get_current_step(self, browser_type: BrowserType) -> Optional[InstallationStep]:
        """Get the current installation step for a browser.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            Current installation step or None if no installation in progress
        """
        return self._installation_progress.get(browser_type)
    
    def is_installation_complete(self, browser_type: BrowserType) -> bool:
        """Check if installation is complete for a browser.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            bool: True if installation is complete
        """
        return self._installation_progress.get(browser_type) == InstallationStep.COMPLETE
