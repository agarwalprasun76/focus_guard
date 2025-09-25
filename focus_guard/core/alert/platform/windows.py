"""
Windows platform implementation for alert functionality.

This module provides Windows-specific implementations of alert functionality
using PowerShell for notifications and Windows API for sound playback.
"""

import os
import sys
import subprocess
import tempfile
import logging
import time
import threading
from typing import Dict, Any, Optional, Tuple

from focus_guard.core.alert.platform.base import PlatformAlertInterface

# Configure logging
logger = logging.getLogger(__name__)


class WindowsAlertPlatform(PlatformAlertInterface):
    """
    Windows-specific implementation of alert functionality.
    
    This class provides Windows-specific implementations of alert functionality
    using PowerShell for notifications and Windows API for sound playback.
    """
    
    def show_notification(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Show a Windows notification using PowerShell.
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
                - app_name: Name of the application causing the alert
                - duration: How long to show the notification (seconds)
                - window_rect: Position and size of the window to show near
                - icon: Path to icon file or icon type
                
        Returns:
            bool: True if notification was shown successfully
        """
        options = options or {}
        
        # Get styling based on alert level
        bg_color, fg_color, sound_type, icon = self._get_alert_style(level)
        
        # Create PowerShell script for notification
        script = self._create_notification_script(
            title=title,
            message=message,
            app_name=options.get("app_name", "FocusGuard"),
            bg_color=bg_color,
            fg_color=fg_color,
            icon=options.get("icon", icon),
            duration=options.get("duration", 10),
            window_rect=options.get("window_rect")
        )
        
        # Run the script in a separate thread to avoid blocking
        if options.get("async", True):
            threading.Thread(
                target=self._run_powershell_script,
                args=(script,),
                daemon=True
            ).start()
            return True
        else:
            return self._run_powershell_script(script)
    
    def play_sound(self, sound_type: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Play a sound alert on Windows.
        
        Args:
            sound_type: Type of sound to play ("normal", "warning", "critical")
            options: Additional options
                - volume: Sound volume (0.0 to 1.0)
                - repeat_count: Number of times to repeat the sound
                - custom_sound: Path to a custom sound file
                
        Returns:
            bool: True if sound was played successfully
        """
        options = options or {}
        volume = options.get("volume", 0.8)
        repeat_count = options.get("repeat_count", 1)
        custom_sound = options.get("custom_sound")
        
        # Map sound_type to actual sound file or system sound
        sound_map = {
            "normal": "SystemAsterisk",
            "warning": "SystemExclamation",
            "critical": "SystemHand"
        }
        sound = sound_map.get(sound_type.lower(), "SystemAsterisk")
        
        try:
            if custom_sound and os.path.exists(custom_sound):
                # Use PowerShell to play custom sound file
                script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Media
                $player = New-Object System.Media.SoundPlayer
                $player.SoundLocation = "{custom_sound.replace('\\', '\\\\')}"
                for ($i = 0; $i -lt {repeat_count}; $i++) {{
                    $player.Play()
                    if ($i -lt {repeat_count - 1}) {{ Start-Sleep -Milliseconds 500 }}
                }}
                """
            else:
                # Use PowerShell to play system sounds
                script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                for ($i = 0; $i -lt {repeat_count}; $i++) {{
                    [System.Media.SystemSounds]::{sound}.Play()
                    if ($i -lt {repeat_count - 1}) {{ Start-Sleep -Milliseconds 500 }}
                }}
                """
            
            # Run in a separate thread to avoid blocking
            threading.Thread(
                target=self._run_powershell_script,
                args=(script,),
                daemon=True
            ).start()
            return True
            
        except Exception as e:
            logger.error(f"Failed to play sound: {e}", exc_info=True)
            return False
    
    def show_blocking_alert(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Show a blocking alert that requires user acknowledgment.
        
        Args:
            title: Title of the alert
            message: Content of the alert
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
                - app_name: Name of the application causing the alert
                - timeout: Timeout in seconds (0 for no timeout)
                - buttons: List of button labels
                - default_button: Index of default button
                
        Returns:
            bool: True if alert was shown and acknowledged
        """
        options = options or {}
        
        # Map level to MessageBox icon
        icon_map = {
            "normal": "Information",
            "warning": "Warning",
            "critical": "Error"
        }
        icon = icon_map.get(level.lower(), "Information")
        
        # Get button configuration
        buttons = options.get("buttons", ["OK"])
        button_str = ", ".join([f'"{btn}"' for btn in buttons])
        default_button = options.get("default_button", 0)
        timeout = options.get("timeout", 0)
        
        # Create PowerShell script for MessageBox
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $result = [System.Windows.Forms.MessageBox]::Show(
            "{message.replace('"', '`"')}",
            "{title.replace('"', '`"')}",
            [System.Windows.Forms.MessageBoxButtons]::{self._get_message_box_buttons(len(buttons))},
            [System.Windows.Forms.MessageBoxIcon]::{icon},
            [System.Windows.Forms.MessageBoxDefaultButton]::Button{default_button + 1}
        )
        $result.ToString()
        """
        
        # Run the script and get the result
        try:
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout if timeout > 0 else None
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning(f"Blocking alert timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Failed to show blocking alert: {e}", exc_info=True)
            return False
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Windows implementation is supported.
        
        Returns:
            bool: True if all dependencies and system requirements are met
        """
        if sys.platform != "win32":
            return False
            
        try:
            # Check if PowerShell is available
            result = subprocess.run(
                ["powershell", "-Command", "echo 'PowerShell is available'"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    # Private helper methods
    
    def _get_alert_style(self, level: str) -> Tuple[str, str, str, str]:
        """
        Get styling properties based on alert level.
        
        Args:
            level: Alert level ("normal", "warning", "critical")
            
        Returns:
            Tuple of (background_color, foreground_color, sound_type, icon)
        """
        styles = {
            "normal": ("#1E90FF", "white", "SystemAsterisk", "Information"),
            "warning": ("#FFA500", "black", "SystemExclamation", "Warning"),
            "critical": ("#FF0000", "white", "SystemHand", "Error")
        }
        return styles.get(level.lower(), styles["normal"])
    
    def _create_notification_script(
        self,
        title: str,
        message: str,
        app_name: str,
        bg_color: str,
        fg_color: str,
        icon: str,
        duration: int,
        window_rect: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Create a PowerShell script for Windows notification.
        
        Args:
            title: Title of the notification
            message: Content of the notification
            app_name: Name of the application
            bg_color: Background color (hex)
            fg_color: Foreground color (hex)
            icon: Icon type or path
            duration: Duration in seconds
            window_rect: Position and size of the window
            
        Returns:
            PowerShell script as string
        """
        # Escape quotes in strings
        title = title.replace('"', '`"')
        message = message.replace('"', '`"')
        app_name = app_name.replace('"', '`"')
        
        # Position the notification near the distraction window if provided
        position_script = ""
        if window_rect:
            x = window_rect.get("x", 0) + window_rect.get("width", 0) // 2
            y = window_rect.get("y", 0) + window_rect.get("height", 0) // 2
            position_script = f"""
            $form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
            $form.Location = New-Object System.Drawing.Point({x}, {y})
            """
        
        # Create the script
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $form = New-Object System.Windows.Forms.Form
        $form.Text = "{app_name}"
        $form.Width = 400
        $form.Height = 200
        $form.BackColor = [System.Drawing.ColorTranslator]::FromHtml("{bg_color}")
        $form.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("{fg_color}")
        $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
        $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
        $form.TopMost = $true
        
        {position_script}
        
        $titleLabel = New-Object System.Windows.Forms.Label
        $titleLabel.Text = "{title}"
        $titleLabel.Font = New-Object System.Drawing.Font("Arial", 12, [System.Drawing.FontStyle]::Bold)
        $titleLabel.AutoSize = $true
        $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
        $form.Controls.Add($titleLabel)
        
        $messageLabel = New-Object System.Windows.Forms.Label
        $messageLabel.Text = "{message}"
        $messageLabel.Font = New-Object System.Drawing.Font("Arial", 10)
        $messageLabel.AutoSize = $true
        $messageLabel.MaximumSize = New-Object System.Drawing.Size(360, 0)
        $messageLabel.Location = New-Object System.Drawing.Point(20, 50)
        $form.Controls.Add($messageLabel)
        
        $okButton = New-Object System.Windows.Forms.Button
        $okButton.Text = "OK"
        $okButton.Location = New-Object System.Drawing.Point(150, 130)
        $okButton.Add_Click({{ $form.Close() }})
        $form.Controls.Add($okButton)
        $form.AcceptButton = $okButton
        
        # Auto-close after duration
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = {duration * 1000}
        $timer.Add_Tick({{
            $timer.Stop()
            $form.Close()
        }})
        $timer.Start()
        
        # Show the form
        $form.Add_Shown({{ $form.Activate() }})
        [void]$form.ShowDialog()
        """
        
        return script
    
    def _run_powershell_script(self, script: str) -> bool:
        """
        Run a PowerShell script and return success status.
        
        Args:
            script: PowerShell script to run
            
        Returns:
            bool: True if script ran successfully
        """
        try:
            # Create a temporary script file
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w") as f:
                f.write(script)
                script_path = f.name
            
            # Run the script
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                capture_output=True,
                text=True
            )
            
            # Clean up
            try:
                os.unlink(script_path)
            except Exception:
                pass
            
            if result.returncode != 0:
                logger.error(f"PowerShell script failed: {result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to run PowerShell script: {e}", exc_info=True)
            return False
    
    def _get_message_box_buttons(self, button_count: int) -> str:
        """
        Get the MessageBoxButtons enum value for the given button count.
        
        Args:
            button_count: Number of buttons
            
        Returns:
            MessageBoxButtons enum value as string
        """
        button_map = {
            1: "OK",
            2: "OKCancel",
            3: "YesNoCancel",
            4: "YesNo",
            5: "RetryCancel",
            6: "AbortRetryIgnore"
        }
        return button_map.get(button_count, "OK")
