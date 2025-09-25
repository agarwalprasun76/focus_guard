"""
UI components for the extension installation guide.

This module provides UI elements for displaying installation instructions
and guiding users through the extension installation process.
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional, List, Any
from pathlib import Path
import webbrowser

from core_v2.browser.models.browser import BrowserType
from core_v2.browser.extension.user_installation.guide import ExtensionInstallationGuide, InstallationStep

logger = logging.getLogger(__name__)


class InstallationGuideUI:
    """UI for guiding users through extension installation."""
    
    def __init__(self, guide: ExtensionInstallationGuide):
        """Initialize the installation guide UI.
        
        Args:
            guide: ExtensionInstallationGuide instance
        """
        self.guide = guide
        self.root = None
        self.current_browser = None
        self.step_labels = []
        self.instruction_text = None
        self.browser_var = None
        
        # Browser icons (would be replaced with actual icons in production)
        self.browser_icons = {
            BrowserType.CHROME: "🌐",
            BrowserType.EDGE: "🌐",
            BrowserType.FIREFOX: "🦊",
            BrowserType.SAFARI: "🧭",
            BrowserType.BRAVE: "🦁",
            BrowserType.OPERA: "🔴",
            BrowserType.VIVALDI: "🎭",
        }
        
    def show(self):
        """Show the installation guide UI."""
        self.root = tk.Tk()
        self.root.title("Focus Guard Extension Installation")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Set window icon (would use actual icon in production)
        # self.root.iconbitmap("path/to/icon.ico")
        
        self._create_widgets()
        self.root.mainloop()
        
    def _create_widgets(self):
        """Create UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Focus Guard Extension Installation", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Browser selection
        browser_frame = ttk.LabelFrame(main_frame, text="Select Browser", padding=10)
        browser_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.browser_var = tk.StringVar()
        
        # Get available browsers
        available_browsers = self._get_available_browsers()
        
        # Create browser selection buttons
        browser_buttons_frame = ttk.Frame(browser_frame)
        browser_buttons_frame.pack(fill=tk.X)
        
        for i, browser_type in enumerate(available_browsers):
            browser_name = browser_type.name.capitalize()
            icon = self.browser_icons.get(browser_type, "🌐")
            
            button = ttk.Button(
                browser_buttons_frame,
                text=f"{icon} {browser_name}",
                command=lambda b=browser_type: self._select_browser(b)
            )
            button.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="ew")
            
        # Configure grid columns to be equal width
        for i in range(3):
            browser_buttons_frame.columnconfigure(i, weight=1)
            
        # Installation steps
        steps_frame = ttk.LabelFrame(main_frame, text="Installation Steps", padding=10)
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create step labels
        for i, step in enumerate(InstallationStep):
            step_name = step.name.replace("_", " ").title()
            step_label = ttk.Label(
                steps_frame,
                text=f"{i+1}. {step_name}",
                foreground="gray"
            )
            step_label.pack(anchor="w", pady=2)
            self.step_labels.append(step_label)
            
        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="Current Instruction", padding=10)
        instructions_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.instruction_text = tk.Text(
            instructions_frame,
            wrap=tk.WORD,
            height=4,
            font=("Arial", 10),
            state="disabled"
        )
        self.instruction_text.pack(fill=tk.BOTH, expand=True)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=tk.X)
        
        self.prev_button = ttk.Button(
            nav_frame,
            text="Previous",
            command=self._previous_step,
            state="disabled"
        )
        self.prev_button.pack(side=tk.LEFT)
        
        self.next_button = ttk.Button(
            nav_frame,
            text="Next",
            command=self._next_step,
            state="disabled"
        )
        self.next_button.pack(side=tk.RIGHT)
        
    def _get_available_browsers(self) -> List[BrowserType]:
        """Get list of available browsers on the system.
        
        Returns:
            List of available browser types
        """
        # Use the browser paths from the guide's extension manager
        available_browsers = []
        for browser_type, path in self.guide._browser_paths.items():
            if path and os.path.exists(path):
                available_browsers.append(browser_type)
                
        return available_browsers
        
    def _select_browser(self, browser_type: BrowserType):
        """Handle browser selection.
        
        Args:
            browser_type: Selected browser type
        """
        self.current_browser = browser_type
        
        # Start installation guide
        success = self.guide.start_installation_guide(browser_type)
        
        if not success:
            messagebox.showerror(
                "Error",
                f"Failed to start installation guide for {browser_type.name}."
            )
            return
            
        # Update UI
        self._update_ui()
        
        # Enable navigation buttons
        self.next_button.config(state="normal")
        
    def _next_step(self):
        """Handle next button click."""
        if not self.current_browser:
            return
            
        # Advance to next step
        success = self.guide.advance_to_next_step(self.current_browser)
        
        if not success:
            messagebox.showinfo(
                "Complete",
                "Installation guide complete!"
            )
            
        # Update UI
        self._update_ui()
        
        # Enable previous button
        self.prev_button.config(state="normal")
        
    def _previous_step(self):
        """Handle previous button click."""
        # Not implemented yet - would need to add this functionality to the guide
        pass
        
    def _update_ui(self):
        """Update UI based on current step."""
        if not self.current_browser:
            return
            
        current_step = self.guide.get_current_step(self.current_browser)
        if not current_step:
            return
            
        # Update step labels
        for i, step in enumerate(InstallationStep):
            if step == current_step:
                self.step_labels[i].config(foreground="blue", font=("Arial", 10, "bold"))
            elif i < list(InstallationStep).index(current_step):
                self.step_labels[i].config(foreground="green", font=("Arial", 10))
            else:
                self.step_labels[i].config(foreground="gray", font=("Arial", 10))
                
        # Update instruction text
        instruction = self.guide._instructions[self.current_browser].get(current_step, "")
        
        self.instruction_text.config(state="normal")
        self.instruction_text.delete("1.0", tk.END)
        self.instruction_text.insert("1.0", instruction)
        self.instruction_text.config(state="disabled")
        
        # Check if we're at the last step
        if current_step == InstallationStep.COMPLETE:
            self.next_button.config(state="disabled")


def launch_installation_guide(extension_dir: Optional[str] = None):
    """Launch the extension installation guide UI.
    
    Args:
        extension_dir: Path to the extension directory. If None, will use default.
    """
    guide = ExtensionInstallationGuide(extension_dir)
    ui = InstallationGuideUI(guide)
    ui.show()
