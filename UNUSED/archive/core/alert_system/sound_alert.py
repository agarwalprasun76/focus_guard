"""
Sound alert provider for FocusGuard.
Plays sound alerts when distractions are detected.
"""
import os
import sys
import subprocess
import threading
import time
from typing import Dict, Any, Optional

from .alert_provider import AlertProvider
from core.logger.logger import get_logger

class SoundAlertProvider(AlertProvider):
    """
    Alert provider that plays sound alerts when distractions are detected.
    Uses platform-specific methods to play sounds.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the sound alert provider.
        
        Args:
            config: Configuration dictionary with optional keys:
                - sound_file: Path to a custom sound file
                - normal_sound: Path to sound file for normal alerts
                - warning_sound: Path to sound file for warning alerts
                - critical_sound: Path to sound file for critical alerts
                - volume: Volume level (0.0 to 1.0)
                - repeat_count: Number of times to repeat the sound
                - repeat_interval: Seconds between repeats
        """
        super().__init__(config or {})
        self.sound_file = self.config.get("sound_file", None)
        self.volume = min(1.0, max(0.0, self.config.get("volume", 0.8)))
        self.repeat_count = self.config.get("repeat_count", 1)
        self.repeat_interval = self.config.get("repeat_interval", 1.0)
        self.enabled = True
        
        # Initialize logger
        self.logger = get_logger("sound_alert")
        
        # Sound files for different alert levels
        self.sound_files = {
            "normal": self.config.get("normal_sound", self.sound_file),
            "warning": self.config.get("warning_sound", self.sound_file),
            "critical": self.config.get("critical_sound", self.sound_file)
        }
        
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Play a sound alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        self.logger.debug(f"SoundAlertProvider.send_alert called with level: {level}")
        
        if not self.enabled:
            self.logger.debug("SoundAlertProvider is disabled, skipping alert")
            return False
            
        self.logger.info(f"Playing sound alert for {window_info.get('app_name', 'Unknown App')}")
        
        # Check for level-specific sound file
        sound_file = self.sound_files.get(level)
        self.logger.debug(f"Level-specific sound file for {level}: {sound_file}")
        
        if sound_file and os.path.exists(sound_file):
            self.logger.debug(f"Found valid sound file: {sound_file}")
            # Play the specific sound file directly
            try:
                if sys.platform == "win32":
                    # Windows sound
                    self.logger.debug("Playing sound using Windows PowerShell")
                    cmd = f"(New-Object Media.SoundPlayer '{sound_file}').PlaySync()"
                    self.logger.debug(f"PowerShell command: {cmd}")
                    result = subprocess.run([
                        "powershell", "-Command", cmd
                    ], capture_output=True, check=False)
                    self.logger.debug(f"PowerShell result: {result.returncode}")
                    if result.stderr:
                        self.logger.debug(f"PowerShell stderr: {result.stderr.decode('utf-8', errors='replace')}")
                    return True
                    
                elif sys.platform == "darwin":
                    # macOS sound
                    self.logger.debug("Playing sound using macOS afplay")
                    subprocess.run([
                        "afplay", sound_file
                    ], capture_output=True, check=False)
                    return True
                    
                elif sys.platform == "linux":
                    # Linux sound (requires paplay or aplay)
                    self.logger.debug("Playing sound using Linux paplay")
                    subprocess.run([
                        "paplay", sound_file
                    ], capture_output=True, check=False)
                    return True
            except Exception as e:
                self.logger.error(f"Failed to play sound file: {e}", exc_info=True)
                # Fall through to default sound handling
        else:
            self.logger.debug("No valid level-specific sound file found, using default sound")
        
        # Start sound in a separate thread to avoid blocking
        self.logger.debug("Starting sound thread with _play_sound")
        thread = threading.Thread(
            target=self._play_sound,
            args=(level,),
            daemon=True
        )
        thread.start()
        return True
        
    def _play_sound(self, level: str):
        """
        Play a sound based on the alert level.
        
        Args:
            level: Alert level ("normal", "warning", or "critical")
        """
        # Select sound based on level
        if level == "critical":
            sound_type = "SystemHand"  # Error sound
            beep_freq = 750
            beep_duration = 500
        elif level == "warning":
            sound_type = "SystemExclamation"  # Warning sound
            beep_freq = 500
            beep_duration = 300
        else:
            sound_type = "SystemAsterisk"  # Information sound
            beep_freq = 400
            beep_duration = 200
            
        # Try to play sound using platform-specific methods
        success = False
        
        # Try custom sound file first if specified
        if self.sound_file and os.path.exists(self.sound_file):
            success = self._play_sound_file(self.sound_file)
            
        # Fall back to system sounds if custom sound failed or wasn't specified
        if not success:
            if sys.platform == "win32":
                success = self._play_windows_sound(sound_type, beep_freq, beep_duration)
            elif sys.platform == "darwin":
                success = self._play_macos_sound()
            elif sys.platform.startswith("linux"):
                success = self._play_linux_sound()
                
        # Fall back to console beep as last resort
        if not success:
            self._console_beep(beep_freq, beep_duration)
            
    def _play_sound_file(self, sound_file: str) -> bool:
        """
        Play a sound file.
        
        Args:
            sound_file: Path to sound file
            
        Returns:
            bool: True if successful
        """
        try:
            if sys.platform == "win32":
                # Use PowerShell to play sound file on Windows
                script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $player = New-Object System.Media.SoundPlayer
                $player.SoundLocation = '{sound_file.replace("'", "''")}'
                $player.PlaySync()
                """
                subprocess.Popen(
                    ["powershell", "-Command", script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            elif sys.platform == "darwin":
                # Use afplay on macOS
                subprocess.Popen(["afplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith("linux"):
                # Try various Linux audio players
                for cmd in ["paplay", "aplay", "play"]:
                    try:
                        subprocess.Popen([cmd, sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
                    except:
                        continue
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error playing sound file: {e}", exc_info=True)
            return False
            
    def _play_windows_sound(self, sound_type: str, beep_freq: int, beep_duration: int) -> bool:
        """
        Play a system sound on Windows.
        
        Args:
            sound_type: System sound type
            beep_freq: Beep frequency in Hz (fallback)
            beep_duration: Beep duration in ms (fallback)
            
        Returns:
            bool: True if successful
        """
        try:
            self.logger.debug(f"Playing Windows sound: {sound_type}")
            
            # Try multiple methods to ensure sound plays
            # Method 1: Direct winsound beep (most reliable)
            try:
                import winsound
                self.logger.debug("Using winsound.Beep directly")
                # For critical alerts, use a sequence of increasingly shrill beeps
                if sound_type == "SystemHand":
                    self.logger.debug("Playing critical shrill beep sequence")
                    # Critical level: High-pitched sequence with increasing frequency
                    frequencies = [800, 1000, 1200, 1400, 1600]
                    durations = [150, 150, 150, 150, 300]
                    for freq, dur in zip(frequencies, durations):
                        winsound.Beep(freq, dur)
                        time.sleep(0.05)
                    # Also play the system sound
                    winsound.MessageBeep(0x10)  # MB_ICONHAND
                    
                elif sound_type == "SystemExclamation":
                    self.logger.debug("Playing warning medium-pitch beep sequence")
                    # Warning level: Medium-pitched sequence
                    frequencies = [600, 800, 1000]
                    durations = [200, 200, 300]
                    for freq, dur in zip(frequencies, durations):
                        winsound.Beep(freq, dur)
                        time.sleep(0.05)
                    # Also play the system sound
                    winsound.MessageBeep(0x30)  # MB_ICONEXCLAMATION
                    
                elif sound_type == "SystemAsterisk":
                    self.logger.debug("Playing normal low-pitch beep")
                    # Normal level: Simple beep
                    winsound.Beep(500, 300)
                    # Also play the system sound
                    winsound.MessageBeep(0x40)  # MB_ICONASTERISK
                    
                else:
                    # Fall back to regular beep
                    winsound.Beep(beep_freq, beep_duration)
                
                # Handle repeat count for all alert types
                for _ in range(1, self.repeat_count):
                    time.sleep(self.repeat_interval)
                    
                    # Repeat the appropriate sound based on level
                    if sound_type == "SystemHand":
                        # Critical level: High-pitched sequence with increasing frequency
                        frequencies = [800, 1000, 1200, 1400, 1600]
                        durations = [150, 150, 150, 150, 300]
                        for freq, dur in zip(frequencies, durations):
                            winsound.Beep(freq, dur)
                            time.sleep(0.05)
                    elif sound_type == "SystemExclamation":
                        # Warning level: Medium-pitched sequence
                        frequencies = [600, 800, 1000]
                        durations = [200, 200, 300]
                        for freq, dur in zip(frequencies, durations):
                            winsound.Beep(freq, dur)
                            time.sleep(0.05)
                    elif sound_type == "SystemAsterisk":
                        # Normal level: Simple beep
                        winsound.Beep(500, 300)
                    else:
                        # Fall back to regular beep
                        winsound.Beep(beep_freq, beep_duration)
                return True
            except Exception as we:
                self.logger.debug(f"winsound.Beep failed: {we}")
            
            # Method 2: PowerShell with direct execution (no window)
            self.logger.debug("Trying PowerShell with direct execution")
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            [System.Media.SystemSounds]::{sound_type}.Play()
            """
            
            # For critical alerts, repeat the sound
            if self.repeat_count > 1:
                script += f"""
                for ($i=1; $i -lt {self.repeat_count}; $i++) {{
                    Start-Sleep -Milliseconds {int(self.repeat_interval * 1000)}
                    [System.Media.SystemSounds]::{sound_type}.Play()
                }}
                """
            
            # Use subprocess.run to wait for completion
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.debug("PowerShell sound played successfully")
                return True
            else:
                self.logger.debug(f"PowerShell sound failed: {result.stderr.decode('utf-8', errors='replace')}")
            
            # Method 3: Save and execute a PowerShell script file
            self.logger.debug("Trying PowerShell with script file")
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w') as temp:
                temp_path = temp.name
                temp.write(f"""
                Add-Type -AssemblyName System.Windows.Forms
                [System.Media.SystemSounds]::{sound_type}.Play()
                Start-Sleep -Seconds 1
                """)
            
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                capture_output=True,
                check=False
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error playing Windows sound: {e}", exc_info=True)
            # Fall back to console beep
            self._console_beep(beep_freq, beep_duration)
            return False
            
    def _play_macos_sound(self) -> bool:
        """
        Play a system sound on macOS.
        
        Returns:
            bool: True if successful
        """
        try:
            # Use AppleScript to play system beep
            script = 'osascript -e "beep"'
            for _ in range(self.repeat_count):
                subprocess.Popen(script, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if _ < self.repeat_count - 1:
                    time.sleep(self.repeat_interval)
            return True
        except Exception as e:
            self.logger.error(f"Error playing macOS sound: {e}", exc_info=True)
            return False
            
    def _play_linux_sound(self) -> bool:
        """
        Play a system sound on Linux.
        
        Returns:
            bool: True if successful
        """
        try:
            # Try to use paplay with system sounds
            sound_file = "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"
            if not os.path.exists(sound_file):
                sound_file = "/usr/share/sounds/ubuntu/stereo/dialog-warning.ogg"
                
            if os.path.exists(sound_file):
                for _ in range(self.repeat_count):
                    subprocess.Popen(["paplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if _ < self.repeat_count - 1:
                        time.sleep(self.repeat_interval)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error playing Linux sound: {e}", exc_info=True)
            return False
            
    def _console_beep(self, frequency: int, duration: int):
        """
        Fall back to console beep.
        
        Args:
            frequency: Beep frequency in Hz
            duration: Beep duration in ms
        """
        try:
            if sys.platform == "win32":
                for _ in range(self.repeat_count):
                    # Use Windows-specific beep function
                    import winsound
                    winsound.Beep(frequency, duration)
                    if _ < self.repeat_count - 1:
                        time.sleep(self.repeat_interval)
            else:
                # Print ASCII bell character for other platforms
                for _ in range(self.repeat_count):
                    # Use logger but still print bell character to console
                    self.logger.debug("Playing console bell character")
                    print("\a", end="", flush=True)
                    if _ < self.repeat_count - 1:
                        time.sleep(self.repeat_interval)
        except Exception as e:
            self.logger.error(f"Error playing console beep: {e}", exc_info=True)
