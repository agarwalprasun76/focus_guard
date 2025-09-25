import sys
import os

# Add the project root to the path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.alert_system.popup_alert import PopupAlertProvider
from core.logger.logger import setup_logger, get_logger

# Set up a logger for testing
logger = setup_logger({
    "log_level": "DEBUG"
})
test_logger = get_logger("test_logging")
test_logger.info("Starting popup alert logging test")

# Create a popup alert provider
popup = PopupAlertProvider({
    "popup_duration": 3
})

# Test sending an alert
test_logger.info("Testing alert with normal level")
popup.send_alert(
    window_info={
        "app_name": "Test App",
        "window_title": "Test Window",
        "process_id": 12345
    },
    message="This is a test alert message",
    level="normal"
)

# Test sending a warning alert
test_logger.info("Testing alert with warning level")
popup.send_alert(
    window_info={
        "app_name": "Test App",
        "window_title": "Test Window",
        "process_id": 12345
    },
    message="This is a warning test alert message",
    level="warning"
)

test_logger.info("Test completed")
