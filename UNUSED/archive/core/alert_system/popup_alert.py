"""
Popup alert provider using platform-native notification methods.
Falls back to simple console alerts if GUI methods aren't available.
"""
import os
import sys
import time
import threading
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional

# Import cross-platform module for window positioning
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.cross_platform.cross_platform import get_window_info

# Import AlertProvider as a base class
from abc import ABC, abstractmethod

# Define a base class here to avoid circular import
class AlertProvider(ABC):
    """Base class for all alert providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the alert provider.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def show_alert(self, title: str, message: str, app_name: str, level: str = "normal") -> bool:
        """Show an alert with the given title and message."""
        pass
        
    @abstractmethod
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """Send an alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        pass
from core.logger.logger import get_logger

class PopupAlertProvider(AlertProvider):
    """Shows popup alerts using platform-specific methods."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        super().__init__(config)
        self.config = config or {}
        self.popup_duration = self.config.get("popup_duration", 10)  # seconds
        self.enabled = self.config.get("enabled", True)  # Enable by default
        self.overlay_on_distraction = self.config.get("overlay_on_distraction", False)  # Whether to show popup on top of distraction
        self.active_alerts = []
        self.recent_alerts = {}  # Track recent alerts to prevent duplicates
        self.logger = get_logger("alert_system.popup")
        
    def show_alert(self, title: str, message: str, app_name: str, level: str = "normal") -> bool:
        """Show an alert with the given title and message.
        
        This method satisfies the AlertProvider abstract base class requirement.
        It creates a simple window_info dict and delegates to send_alert.
        
        Args:
            title: Alert title
            message: Alert message
            app_name: Name of the application
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        # Create a simple window_info dict with the app_name
        window_info = {"app_name": app_name}
        
        # If overlay_on_distraction is enabled, try to find the window
        if self.overlay_on_distraction:
            window_rect = self._find_window_position(app_name)
            if window_rect:
                window_info["rect"] = window_rect
        
        # Delegate to the send_alert method
        return self.send_alert(window_info, message, level)
        
    def _find_window_position(self, app_name):
        """Find the position of a window by app name using cross-platform module.
        
        Args:
            app_name: Name of the application to find
            
        Returns:
            tuple: (left, top, right, bottom) coordinates or None if not found
        """
        try:
            if sys.platform != "win32":
                return None
                
            import win32gui
            
            # Get all top-level windows
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_info = get_window_info(hwnd)
                    if window_info:
                        windows.append(window_info)
                return True
                
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            # Find windows matching the app name
            matching_windows = []
            for window in windows:
                if app_name.lower() in window["app_name"].lower():
                    matching_windows.append(window)
                    
            # Sort by window area (largest first)
            if matching_windows:
                matching_windows.sort(key=lambda w: w["area"], reverse=True)
                self.logger.debug(f"Found {len(matching_windows)} windows for {app_name}")
                self.logger.debug(f"Using window: {matching_windows[0]['window_title']}")
                return matching_windows[0]["rect"]
                
        except Exception as e:
            self.logger.error(f"Error finding window position: {e}", exc_info=True)
            
        return None
        
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Show a popup alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        self.logger.debug(f"PopupAlertProvider.send_alert called with level: {level}")
        
        if not self.enabled:
            self.logger.debug("PopupAlertProvider is disabled, skipping alert")
            return False
            
        app_name = window_info.get("app_name", "Unknown App")
        
        # Check for duplicate alerts - prevent showing the same alert level for the same app in quick succession
        current_time = time.time()
        alert_key = f"{app_name}-{level}"
        
        if alert_key in self.recent_alerts:
            last_alert_time = self.recent_alerts[alert_key]
            time_since_last = current_time - last_alert_time
            
            # If we've shown this exact alert recently, skip it
            if time_since_last < self.popup_duration:
                self.logger.debug(f"Skipping duplicate alert for {app_name} at level {level} (shown {time_since_last:.1f}s ago)")
                return True  # Return True because we're handling the alert appropriately
        
        # Track this alert to prevent duplicates
        self.recent_alerts[alert_key] = current_time
        
        self.logger.info(f"Creating popup alert for {app_name} at level {level}")
        
        # Start popup in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._show_platform_popup,
            args=(window_info, message, level),
            daemon=True
        )
        thread.start()
        return True
        
    def _show_platform_popup(self, window_info: Dict[str, Any], message: str, level: str):
        """Show a popup using platform-specific methods."""
        app_name = window_info.get("app_name", "Unknown App")
        title = f"FocusGuard Alert - {level.capitalize()}"
        
        self.logger.debug(f"_show_platform_popup called for {app_name} with level: {level}")
        
        try:
            # Track this alert
            alert_id = self._create_alert_id(app_name)
            self.logger.debug(f"Created alert_id: {alert_id}")
            
            # Show platform-specific popup
            self.logger.debug(f"Calling _show_popup_for_platform for platform: {sys.platform}")
            self._show_popup_for_platform(title, message, app_name, level)
                
            # Remove from active alerts after duration
            self.logger.debug(f"Scheduling alert cleanup with duration: {self.popup_duration}s")
            self._schedule_alert_cleanup(alert_id)
                
        except Exception as e:
            self.logger.error(f"Failed to show popup alert: {e}", exc_info=True)
            # No need for explicit traceback printing as exc_info=True includes it
    
    def _create_alert_id(self, app_name: str) -> str:
        """Create and track a unique ID for this alert."""
        alert_id = f"{app_name}-{time.time()}"
        self.active_alerts.append(alert_id)
        return alert_id
    
    def _schedule_alert_cleanup(self, alert_id: str):
        """Schedule cleanup of the alert after the popup duration."""
        if self.popup_duration > 0:
            time.sleep(self.popup_duration)
            if alert_id in self.active_alerts:
                self.active_alerts.remove(alert_id)
    
    def _show_popup_for_platform(self, title: str, message: str, app_name: str, level: str):
        """Show popup using the appropriate method for the current platform."""
        self.logger.debug(f"_show_popup_for_platform called for platform: {sys.platform}")
        
        # Windows - use PowerShell for a toast notification
        if sys.platform == "win32":
            self.logger.debug("Detected Windows platform, calling _show_windows_popup")
            self._show_windows_popup(title, message, app_name, level)
            
        # macOS - use AppleScript for a notification
        elif sys.platform == "darwin":
            self.logger.debug("Detected macOS platform, calling _show_macos_popup")
            self._show_macos_popup(title, message, app_name, level)
            
        # Linux - use notify-send
        elif sys.platform == "linux":
            self.logger.debug("Detected Linux platform, calling _show_linux_popup")
            self._show_linux_popup(title, message, app_name, level)
            
        # Fallback to console alert
        else:
            self.logger.debug("Unknown platform, falling back to console popup")
            self._show_console_popup(title, message, app_name, level)
            
    def _show_windows_popup(self, title: str, message: str, app_name: str, level: str):
        """Show an enhanced Windows popup with sound effects."""
        self.logger.debug(f"_show_windows_popup called for {app_name} with level: {level}")
        try:
            # Escape single quotes in message and title
            safe_message = message.replace("'", "''")
            safe_title = title.replace("'", "''")
            
            # Get styling based on alert level
            self.logger.debug("Getting alert style")
            style = self._get_alert_style(level)
            self.logger.debug(f"Alert style: {style}")
            
            # Find window position if overlay_on_distraction is enabled
            self.window_rect = None
            if self.overlay_on_distraction:
                self.logger.debug(f"Looking for window position for {app_name}")
                self.window_rect = self._find_window_position(app_name)
                self.logger.debug(f"Found window position: {self.window_rect}")
                
                # Ensure we have valid window coordinates
                if self.window_rect and len(self.window_rect) == 4:
                    self.logger.debug(f"Valid window coordinates found: {self.window_rect}")
                else:
                    self.logger.warning(f"Invalid window coordinates, will use center screen: {self.window_rect}")
                    self.window_rect = None
            
            # Add window position to style if found
            if self.window_rect:
                style["window_rect"] = self.window_rect
            
            # Create the PowerShell script
            self.logger.debug("Creating PowerShell script")
            script = self._create_windows_popup_script(
                safe_title, safe_message, app_name, 
                style["bg_color"], style["fg_color"], 
                style["sound"], style["icon"],
                style.get("window_rect")
            )
            self.logger.debug(f"PowerShell script length: {len(script)} characters")
            
            # Run the PowerShell script without waiting
            self.logger.debug("Running PowerShell script")
            self._run_powershell_script(script, message)
            
            # Also print to console for backup
            self.logger.debug("Showing console popup as backup")
            self._show_console_popup(title, message, app_name, level)
            
        except Exception as e:
            self.logger.error(f"Windows popup error: {e}", exc_info=True)
            self._show_console_popup(title, message, app_name, level)
    
    def _get_alert_style(self, level: str) -> Dict[str, str]:
        """Get styling properties based on alert level."""
        if level == "critical":
            return {
                "bg_color": "Red",  # Bright red
                "fg_color": "White",  # White text
                "sound": "SystemHand",  # Error sound
                "icon": "Error",
                "size": "600x300"  # Larger for critical alerts
            }
        elif level == "warning":
            return {
                "bg_color": "Orange",  # Orange
                "fg_color": "Black",  # Black text
                "sound": "SystemExclamation",  # Warning sound
                "icon": "Warning",
                "size": "550x250"  # Medium for warnings
            }
        else:  # normal
            return {
                "bg_color": "DodgerBlue",  # Blue
                "fg_color": "Black",  # Black text
                "sound": "SystemNotification",  # Information sound
                "icon": "Information",
                "size": "500x200"  # Standard size
            }
    
    def _create_windows_popup_script(self, title, message, app_name, bg_color, fg_color, sound, icon, window_rect=None):
        """Create a simple PowerShell script for Windows popup."""
        # Create a much simpler script that's less likely to cause errors
        
        # Set the icon and sound based on alert level
        if icon == "Error":
            ps_icon = "Error"
            ps_sound = "Hand"
            bg_color_name = "LightPink"
        elif icon == "Warning":
            ps_icon = "Warning"
            ps_sound = "Exclamation"
            bg_color_name = "LightYellow"
        else:
            ps_icon = "Information"
            ps_sound = "Asterisk"
            bg_color_name = "LightBlue"
        
        # Escape special characters
        safe_title = title.replace('"', '`"').replace("'", "''")
        safe_message = message.replace('"', '`"').replace("'", "''")
        safe_app_name = app_name.replace('"', '`"').replace("'", "''")
        
        # Create a simple script
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        # Play sound
        [System.Media.SystemSounds]::{ps_sound}.Play()
        
        # Create form
        $form = New-Object System.Windows.Forms.Form
        $form.Text = '{safe_app_name} Alert'
        $form.Size = New-Object System.Drawing.Size(400, 200)
        $form.TopMost = $true
        
        # Position the form - center on distraction window if coordinates are available
        if ($env:OVERLAY_ON_DISTRACTION -eq "True") {{
            if ($env:WINDOW_LEFT -and $env:WINDOW_TOP -and $env:WINDOW_RIGHT -and $env:WINDOW_BOTTOM) {{
                try {{
                    # Calculate window center
                    $windowLeft = [int]$env:WINDOW_LEFT
                    $windowTop = [int]$env:WINDOW_TOP
                    $windowRight = [int]$env:WINDOW_RIGHT
                    $windowBottom = [int]$env:WINDOW_BOTTOM
                    
                    $windowWidth = $windowRight - $windowLeft
                    $windowHeight = $windowBottom - $windowTop
                    $windowCenterX = $windowLeft + ($windowWidth / 2)
                    $windowCenterY = $windowTop + ($windowHeight / 2)
                    
                    # Calculate form position (centered on window)
                    $formX = $windowCenterX - ($form.Width / 2)
                    $formY = $windowCenterY - ($form.Height / 2)
                    
                    # Set form position
                    $form.StartPosition = 'Manual'
                    $form.Location = New-Object System.Drawing.Point($formX, $formY)
                }} catch {{
                    $form.StartPosition = 'CenterScreen'
                }}
            }} else {{
                $form.StartPosition = 'CenterScreen'
            }}
        }} else {{
            $form.StartPosition = 'CenterScreen'
        }}
        
        $form.BackColor = [System.Drawing.Color]::{bg_color_name}
        $form.FormBorderStyle = 'FixedDialog'
        $form.MaximizeBox = $false
        $form.MinimizeBox = $false
        
        # Create title label
        $titleLabel = New-Object System.Windows.Forms.Label
        $titleLabel.Text = '{safe_title}'
        $titleLabel.Font = New-Object System.Drawing.Font('Arial', 12, [System.Drawing.FontStyle]::Bold)
        $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
        $titleLabel.Size = New-Object System.Drawing.Size(360, 25)
        $form.Controls.Add($titleLabel)
        
        # Create message label
        $messageLabel = New-Object System.Windows.Forms.Label
        $messageLabel.Text = '{safe_message}'
        $messageLabel.Font = New-Object System.Drawing.Font('Arial', 10)
        $messageLabel.Location = New-Object System.Drawing.Point(20, 50)
        $messageLabel.Size = New-Object System.Drawing.Size(360, 100)
        $messageLabel.AutoSize = $true
        $form.Controls.Add($messageLabel)
        
        # Auto-close timer
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = {self.popup_duration * 1000}
        $timer.Add_Tick({{$form.Close(); $timer.Stop()}})
        $timer.Start()
        
        # Show form
        $form.ShowDialog() | Out-Null
        """
        
        # Set environment variables for window positioning if available
        if window_rect:
            os.environ["OVERLAY_ON_DISTRACTION"] = "True"
            os.environ["WINDOW_LEFT"] = str(window_rect[0])
            os.environ["WINDOW_TOP"] = str(window_rect[1])
            os.environ["WINDOW_RIGHT"] = str(window_rect[2])
            os.environ["WINDOW_BOTTOM"] = str(window_rect[3])
        else:
            os.environ["OVERLAY_ON_DISTRACTION"] = "False"
        
        return script
    
    def _run_powershell_script(self, script: str, message: str = ""):
        """Run a PowerShell script asynchronously."""
        self.logger.debug("Inside _run_powershell_script")
        
        try:
            # Save script to a temporary file for better execution
            import tempfile
            import os
            
            # Log the script content for debugging
            self.logger.debug("PowerShell script content (first 500 chars):")
            self.logger.debug(script[:500] + "..." if len(script) > 500 else script)
            
            # First try with UTF-8 encoding
            try:
                # Use UTF-8 encoding to handle Unicode characters like emojis
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w', encoding='utf-8') as temp:
                    temp_path = temp.name
                    # Clean any problematic Unicode characters that might cause issues
                    clean_script = self._clean_unicode_for_powershell(script)
                    temp.write(clean_script)
                    self.logger.debug(f"Saved script to temporary file with UTF-8 encoding: {temp_path}")
            except UnicodeEncodeError as e:
                # If UTF-8 fails, fall back to ASCII with replacement
                self.logger.warning(f"UTF-8 encoding failed: {e}")
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w', encoding='ascii', errors='replace') as temp:
                    temp_path = temp.name
                    temp.write(script)
                    self.logger.debug(f"Saved script to temporary file with ASCII encoding: {temp_path}")
            
            # Set up environment variables for the PowerShell script
            env = os.environ.copy()
            env["OVERLAY_ON_DISTRACTION"] = str(self.overlay_on_distraction)
            self.logger.debug(f"Setting OVERLAY_ON_DISTRACTION={self.overlay_on_distraction}")
            
            # Pass window coordinates if available
            if hasattr(self, 'window_rect') and self.window_rect:
                left, top, right, bottom = self.window_rect
                env["WINDOW_LEFT"] = str(left)
                env["WINDOW_TOP"] = str(top)
                env["WINDOW_RIGHT"] = str(right)
                env["WINDOW_BOTTOM"] = str(bottom)
                self.logger.debug(f"Passing window coordinates: {left},{top},{right},{bottom}")
            
            # Use -ExecutionPolicy Bypass to ensure script runs
            self.logger.debug("Launching PowerShell process with ExecutionPolicy Bypass")
            
            # Use a simpler approach - just run the script from the file
            # This is more reliable than passing the script directly
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path]
            self.logger.debug(f"Running PowerShell command: {cmd[0]} {cmd[1]} {cmd[2]} -File {temp_path}")
            
            # Run the process with a timeout
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                self.logger.debug(f"PowerShell process launched with PID: {process.pid}")
                
                # Capture output with timeout
                stdout, stderr = process.communicate(timeout=2)
                if stdout:
                    self.logger.debug(f"PowerShell stdout: {stdout.decode('utf-8', errors='replace')}")
                if stderr:
                    self.logger.error(f"PowerShell stderr: {stderr.decode('utf-8', errors='replace')}")
                    
                # Check return code
                if process.returncode != 0:
                    self.logger.error(f"PowerShell process exited with code {process.returncode}")
                    stderr = True  # Set stderr to True to trigger fallback
                else:
                    self.logger.debug("PowerShell process completed successfully")
                    stderr = False  # Clear stderr to avoid fallback
                    
            except subprocess.TimeoutExpired:
                self.logger.debug("PowerShell process is running asynchronously")
                stderr = False  # Don't trigger fallback for async processes
            except Exception as e:
                self.logger.error(f"Error running PowerShell: {e}")
                stderr = True  # Trigger fallback on any exception
            
            # Only run a simple test popup if both command-based and file-based approaches failed
            if stderr:
                self.logger.debug("Both approaches failed, running a simple test popup as fallback")
                # Escape special characters in the message
                safe_message = message.replace('"', '`"').replace("'", "''")
                
                test_cmd = ["powershell", "-Command", f"""
                Add-Type -AssemblyName System.Windows.Forms
                
                # Play a sound based on severity
                [System.Media.SystemSounds]::Exclamation.Play()
                
                $form = New-Object System.Windows.Forms.Form
                $form.Text = 'FocusGuard Alert'
                $form.Size = New-Object System.Drawing.Size(400, 200)
                $form.StartPosition = 'CenterScreen'
                $form.TopMost = $true
                $form.BackColor = [System.Drawing.Color]::LightYellow
                
                $titleLabel = New-Object System.Windows.Forms.Label
                $titleLabel.Text = '{title}'
                $titleLabel.Font = New-Object System.Drawing.Font('Arial', 12, [System.Drawing.FontStyle]::Bold)
                $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
                $titleLabel.Size = New-Object System.Drawing.Size(360, 25)
                $form.Controls.Add($titleLabel)
                
                $messageLabel = New-Object System.Windows.Forms.Label
                $messageLabel.Text = '{safe_message}'
                $messageLabel.Font = New-Object System.Drawing.Font('Arial', 10)
                $messageLabel.Location = New-Object System.Drawing.Point(20, 50)
                $messageLabel.Size = New-Object System.Drawing.Size(360, 100)
                $messageLabel.AutoSize = $true
                $form.Controls.Add($messageLabel)
                
                $timer = New-Object System.Windows.Forms.Timer
                $timer.Interval = 5000
                $timer.Add_Tick({{$form.Close(); $timer.Stop()}})
                $timer.Start()
                
                $form.ShowDialog()
                """]
                
                try:
                    subprocess.Popen(test_cmd)
                    self.logger.debug("Launched fallback popup alert")
                except Exception as e:
                    self.logger.error(f"Failed to launch fallback popup: {e}")
                    # Last resort: show console popup
                    self._show_console_popup(title, message, "FocusGuard", "warning")
            
            # No need for output capture thread as we're already capturing output
            
            # Check if process started correctly
            if process.poll() is not None:
                self.logger.debug(f"Process exited immediately with code: {process.returncode}")
                stdout, stderr = process.communicate()
                if stdout:
                    self.logger.debug(f"PowerShell stdout: {stdout.decode('utf-8', errors='replace')}")
                if stderr:
                    self.logger.debug(f"PowerShell stderr: {stderr.decode('utf-8', errors='replace')}")
            else:
                self.logger.debug("PowerShell process is running")
                
        except Exception as e:
            self.logger.error(f"Error running PowerShell script: {e}", exc_info=True)
            
    def _show_macos_popup(self, title: str, message: str, app_name: str, level: str):
        """Show a macOS notification."""
        try:
            # Escape quotes in message
            message = message.replace('"', '\\"')
            
            # Use AppleScript to display notification
            subprocess.run([
                "osascript", "-e", 
                f'display notification "{message}" with title "{title}"'
            ], capture_output=True, check=False)
            
        except Exception as e:
            self.logger.error(f"macOS popup error: {e}", exc_info=True)
            self._show_console_popup(title, message, app_name, level)
            
    def _show_linux_popup(self, title: str, message: str, app_name: str, level: str):
        """Show a Linux notification."""
        try:
            # Use notify-send for Linux
            urgency = "normal"
            if level == "critical":
                urgency = "critical"
                
            subprocess.run([
                "notify-send", title, message, 
                f"--urgency={urgency}", "--icon=dialog-warning"
            ], capture_output=True, check=False)
            
        except Exception as e:
            self.logger.error(f"Linux popup error: {e}", exc_info=True)
            self._show_console_popup(title, message, app_name, level)
            
    def _show_console_popup(self, title: str, message: str, app_name: str, level: str):
        """Show a console-based alert as fallback."""
        border = "=" * 60
        try:
            # Try to print with Unicode characters
            console_message = f"\n{border}\n\033[1m{title}\033[0m\n{border}\nApp: {app_name}\nMessage: {message}\nLevel: {level}\n{border}\n"
            # Log at appropriate level based on alert level
            if level == "critical":
                self.logger.critical(console_message)
            elif level == "warning":
                self.logger.warning(console_message)
            else:
                self.logger.info(console_message)
            
            # Still print to console for immediate visibility
            print(console_message)
        except UnicodeEncodeError:
            # Fall back to ASCII-only if Unicode fails
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            console_message = f"\n{border}\nFocusGuard Alert\n{border}\nApp: {app_name}\nMessage: {safe_message}\nLevel: {level}\n{border}\n"
            
            # Log at appropriate level based on alert level
            if level == "critical":
                self.logger.critical(console_message)
            elif level == "warning":
                self.logger.warning(console_message)
            else:
                self.logger.info(console_message)
                
            # Still print to console for immediate visibility
            print(console_message)
        
    def _clean_unicode_for_powershell(self, text):
        """Clean Unicode characters that might cause issues in PowerShell scripts.
        
        Args:
            text: The text to clean
            
        Returns:
            str: Cleaned text safe for PowerShell
        """
        # Replace zero-width spaces with regular spaces
        text = text.replace('\u200b', ' ')
        
        # Replace emojis and other problematic Unicode characters
        import re
        # This regex matches emoji characters and other non-ASCII characters that might cause issues
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]+"
        )
        text = emoji_pattern.sub('', text)
        
        # Replace any remaining non-ASCII characters with '?'
        text = ''.join(c if ord(c) < 128 else '?' for c in text)
        
        return text
        
    def close_all(self):
        """Clear all active alerts."""
        self.active_alerts = []
