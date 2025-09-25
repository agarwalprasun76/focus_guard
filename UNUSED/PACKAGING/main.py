"""
FocusGuard – Adaptive Focus & Distraction Monitor
Entry point for the application. Handles config loading, task selection, and polling loop.
"""
import sys
import base64
import os
import time
from PIL import ImageGrab
from pathlib import Path
from datetime import datetime
from core.task_manager import TaskManager
from core.activity_monitor.activity_monitor import ActivityMonitor
from core.distraction_detector.distraction_detector import DistractionDetector
from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider
from core.alert_system.email_alert import EmailAlertProvider
from core.logger.logger import setup_logger, get_logger
from core.config.simple_config_manager import ConfigManager
from utils.time_utils import get_current_time

# Track if we've already taken a screenshot for the current session
_screenshot_taken = {}

def take_screenshot(app_name=None):
    """Take a screenshot and return it as base64 encoded string.
    
    Args:
        app_name: Name of the application causing the distraction.
                 If provided, only one screenshot will be taken per app per session.
    """
    global _screenshot_taken
    
    # If app_name is provided, check if we've already taken a screenshot for this app
    if app_name and app_name in _screenshot_taken:
        return _screenshot_taken[app_name]
    
    try:
        # Create temp directory if it doesn't exist
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        # Use a unique filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = temp_dir / f"screenshot_{timestamp}.png"
        
        # Capture the screen
        screenshot = ImageGrab.grab()
        screenshot.save(temp_file)
        
        # Read the file and encode as base64
        with open(temp_file, "rb") as f:
            screenshot_data = base64.b64encode(f.read()).decode("utf-8")
            
        # Clean up the temporary file
        temp_file.unlink()
        
        # If we have more than 5 files in the temp directory, clean up old ones
        screenshot_files = list(temp_dir.glob("screenshot_*.png"))
        if len(screenshot_files) > 5:
            # Sort by modification time and delete the oldest ones
            screenshot_files.sort(key=lambda x: x.stat().st_mtime)
            for old_file in screenshot_files[:-5]:  # Keep the 5 newest files
                try:
                    old_file.unlink()
                except Exception:
                    pass
        
        # Store the screenshot data for this app if app_name is provided
        if app_name:
            _screenshot_taken[app_name] = screenshot_data
        
        return screenshot_data
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None

def safe_log(logger, level, msg):
    """Log a message safely, handling encoding errors."""
    try:
        if level == "debug":
            logger.debug(msg)
        elif level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "critical":
            logger.critical(msg)
    except UnicodeEncodeError:
        # If there's an encoding error, try to encode to ASCII and log that
        safe_msg = msg.encode('ascii', errors='replace').decode()
        if level == "debug":
            logger.debug(safe_msg)
        elif level == "info":
            logger.info(safe_msg)
        elif level == "warning":
            logger.warning(safe_msg)
        elif level == "error":
            logger.error(safe_msg)
        elif level == "critical":
            logger.critical(safe_msg)

def main() -> None:
    """
    Main entry point for FocusGuard.
    Follows the high-level process:
    1. Load configuration
    2. Initialize logger
    3. Initialize alert system with providers
    4. Initialize distraction detector
    5. Begin monitoring loop:
        - Get active window/app (activity_monitor)
        - Distraction check (distraction_detector)
        - Trigger alert/log if needed (alert_system)
        - End session, save logs
    """
    
    # 1. Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # 2. Initialize the logger
    log_level = config.get("data_storage", {}).get("log_level", "DEBUG")
    setup_logger({
        "log_level": log_level
    })
    logger = get_logger("main")
    logger.info("FocusGuard starting with configuration from: " + str(config_manager.get_config_path()))
    
    # 3. Initialize submodules
    activity_monitor = ActivityMonitor()
    
    # Initialize the alert system with config settings
    alert_system_config = config.get("alert_system", {})
    alert_system = AlertSystem(config={
        "cooldown_period": alert_system_config.get("cooldown_period", 60),
        "escalation_threshold": alert_system_config.get("escalation_threshold", 3),
        "escalation_window": alert_system_config.get("escalation_window", 300)
    })
    
    # Add popup alert provider if enabled
    popup_config = alert_system_config.get("providers", {}).get("popup", {})
    if popup_config.get("enabled", True):
        popup_provider = PopupAlertProvider(config={
            "popup_duration": popup_config.get("popup_duration", 10),
            "enabled": True
        })
        alert_system.add_provider(popup_provider)
        logger.info("Popup alerts enabled")
    
    # Add sound alert provider if enabled
    sound_config = alert_system_config.get("providers", {}).get("sound", {})
    if sound_config.get("enabled", True):
        sound_provider = SoundAlertProvider(config={
            "volume": sound_config.get("volume", 0.8),
            "repeat_count": sound_config.get("repeat_count", 2),
            "repeat_interval": sound_config.get("repeat_interval", 0.5)
        })
        alert_system.add_provider(sound_provider)
        logger.info("Sound alerts enabled")
    
    # Add email alert provider if enabled
    email_config = alert_system_config.get("providers", {}).get("email", {})
    if email_config.get("enabled", True):
        # Create a safe copy of the email config to avoid modifying the original
        email_provider_config = {
            "email_recipient": email_config.get("email_recipient", config.get("user", {}).get("parent_email", "")),
            "smtp_server": email_config.get("smtp_server", "smtp.gmail.com"),
            "smtp_port": email_config.get("smtp_port", 587),
            "smtp_username": email_config.get("smtp_username", ""),
            "smtp_password": email_config.get("smtp_password", ""),
            "use_tls": email_config.get("use_tls", True),
            "from_name": email_config.get("from_name", "FocusGuard App"),
            "subject_prefix": email_config.get("subject_prefix", "FocusGuard Alert"),
            "max_emails_per_day": email_config.get("max_emails_per_day", 5),
            "include_screenshot": email_config.get("include_screenshot", True),
            "critical_only": email_config.get("critical_only", True)  # Only send emails for critical alerts by default
        }
        
        # Only add the email provider if we have the required settings
        if email_provider_config["email_recipient"] and email_provider_config["smtp_username"]:
            email_provider = EmailAlertProvider(email_provider_config)
            alert_system.add_provider(email_provider)
            logger.info(f"Email alerts enabled for {email_provider_config['email_recipient']}")
            
            if email_provider_config["include_screenshot"]:
                logger.info("Email screenshots enabled for critical alerts")
        else:
            logger.warning("Email alerts disabled: missing recipient or SMTP username")
    
    # Log confirmation of alert system initialization
    logger.info(f"Alert system initialized with cooldown period: {alert_system.cooldown_period} seconds")
    logger.info(f"Alert escalation threshold: {alert_system.escalation_threshold} alerts within {alert_system.escalation_window} seconds")
    
    # Initialize distraction detector with alert callback
    distraction_detection_config = config.get("distraction_detection", {})
    allowed_apps = distraction_detection_config.get("allowed_apps", ["Windsurf.exe"])
    
    distraction_detector = DistractionDetector(
        allowed_apps=allowed_apps,
        alert_callback=alert_system.alert  # Connect the alert system
    )
    
    # logger = Logger()  # Not implemented yet
    # TODO: data_storage integration

    # 4. Begin monitoring loop
    # Get monitoring settings from config
    monitoring_config = config.get("monitoring", {})
    check_interval = monitoring_config.get("check_interval", 10)  # seconds
    session_duration = monitoring_config.get("session_duration", 60)  # seconds
    
    # Calculate iterations based on check interval and session duration
    iterations = max(1, int(session_duration / check_interval))
    
    logger.info(f"Monitoring started. Will check every {check_interval} seconds for {session_duration} seconds.")
    logger.info(f"Session will run for {iterations} checks and then exit.")
    
    # 4. Monitoring loop with strict session duration enforcement
    import time
    import datetime
    
    try:
        checks = 0
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=session_duration)
        
        # Use both iteration count and absolute time as exit conditions
        while checks < iterations and datetime.datetime.now() < end_time:
            logger.debug(f"Loop iteration {checks+1}/{iterations}")
            window_info = activity_monitor.get_active_window()  # uses cross_platform
            logger.debug(f"window_info: {window_info}")
            
            if not window_info:
                logger.info("No active window detected.")
            else:
                # Active window distraction logic
                is_distraction = distraction_detector.is_distracted(window_info)
                app_name = window_info.get('app_name', '').lower()
                window_title = window_info.get('window_title', '').lower()
                if is_distraction:
                    logger.warning(f"DISTRACTION - {app_name}: '{window_title}' (ACTIVE)")
                    # Update activity to trigger alerts
                    distraction_detector.update_activity(window_info)
                    
                    # Explicitly trigger an alert for the distraction
                    message = f"Distraction detected: {app_name}\n{window_title}"
                    logger.warning(f"Directly triggering alert for {app_name}")
                    
                    # Take screenshot for ALL alerts - we'll only use it for critical ones
                    # but we need to capture it early since the first alert might become critical
                    # due to escalation
                    screenshot_data = take_screenshot(app_name)
                    if screenshot_data:
                        window_info["screenshot"] = screenshot_data
                        logger.info(f"Screenshot captured - size: {len(screenshot_data)} bytes")
                    else:
                        logger.error("Failed to capture screenshot")
                        
                    # Check the alert level for logging purposes
                    alert_count = alert_system._count_recent_alerts(app_name)
                    
                    alert_system.alert(window_info, message)
                else:
                    logger.info(f"FOCUS - {app_name}: '{window_title}' (ACTIVE)")

            # Top window distraction detection
            windows = activity_monitor.get_top_windows(top_region=200)
            active_hwnd = window_info.get('hwnd') if window_info else None
            for w in windows:
                area = w.get('area', 0)
                hwnd = w.get('hwnd', None)
                is_behind_active = (hwnd != active_hwnd and hwnd is not None and active_hwnd is not None)
                percent = f"{w.get('percent', 0) * 100:.1f}%"
                logger.debug(f"TOP WINDOW - {w.get('app_name','')}: '{w.get('window_title','')}', area={area}, percent={percent}, hwnd={hwnd}, behind_active={is_behind_active}")

            # Hybrid stateful + rule-based distraction detection
            distraction_events = distraction_detector.update_and_detect(window_info, windows)
            if distraction_events:
                for event in distraction_events:
                    logger.warning(f"DISTRACTION EVENT - {event}")
                    
                    # Trigger an alert for each distraction event
                    if window_info:  # Make sure we have window info
                        message = f"Distraction event: {event}"
                        logger.warning(f"Triggering alert for distraction event: {event}")
                        
                        # Add screenshot for critical alerts
                        app_name = window_info.get('app_name', '')
                        alert_count = alert_system._count_recent_alerts(app_name)
                        
                        if alert_count >= alert_system.escalation_threshold * 2:  # Only for critical level
                            logger.warning(f"Taking screenshot for critical distraction event: {event} (alert count: {alert_count})")
                            screenshot_data = take_screenshot()
                            if screenshot_data:
                                window_info["screenshot"] = screenshot_data
                                logger.info("Screenshot attached to distraction event alert")
                        
                        alert_system.alert(window_info, message)
            else:
                logger.info("FOCUS - RULES - No distraction events detected.")

            # Persistent state check for active window
            if window_info and distraction_detector.is_distracted(window_info):
                app_name = window_info.get('app_name','')
                logger.warning(f"DISTRACTION - You are still distracted by {app_name} (ACTIVE)")
                # Update activity in distraction detector to trigger alerts if needed
                distraction_detector.update_activity(window_info)
                
                # Only trigger a new alert every other check (to avoid too many alerts)
                if checks % 2 == 0:
                    message = f"Still distracted by {app_name}\nPlease return to your focused task."
                    logger.warning(f"Triggering follow-up alert for {app_name}")
                    
                    # Add screenshot for critical alerts
                    alert_count = alert_system._count_recent_alerts(app_name)
                    
                    if alert_count >= alert_system.escalation_threshold * 2:  # Only for critical level
                        logger.warning(f"Taking screenshot for persistent critical distraction: {app_name} (alert count: {alert_count})")
                        screenshot_data = take_screenshot()
                        if screenshot_data:
                            window_info["screenshot"] = screenshot_data
                            logger.info("Screenshot attached to persistent distraction alert")
                    
                    alert_system.alert(window_info, message)

            # Persistent state check for top windows
            for w in windows:
                if distraction_detector.is_distracted(w):
                    logger.warning(f"DISTRACTION - You are still distracted by {w.get('app_name','')} (TOP WINDOW)")
            
            # Sleep and increment counter
            logger.debug(f"Sleeping for {check_interval} seconds...")
            time.sleep(check_interval)
            checks += 1
        
        logger.info(f"Monitoring session complete after {checks} checks.")
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logger.info("FocusGuard session ended.")

if __name__ == "__main__":
    main()
