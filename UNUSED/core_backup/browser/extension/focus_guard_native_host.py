#!/usr/bin/env python
"""
FocusGuard Native Messaging Host

This script handles communication between browser extensions and the FocusGuard application.
It receives messages from browser extensions via stdin and can send replies via stdout.

Communication protocol:
- stdin  ← extension JSON messages
- stdout → optional replies (not needed for tab snapshots)

The native host primarily receives tab snapshots from browser extensions and
saves them to a local file for the FocusGuard application to process.
"""

import sys
import json
import struct
import os
import getpass
import traceback
import datetime
import tempfile
import atexit
import signal
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- Logging Setup ---
def setup_logging():
    """Set up logging for the native messaging host."""
    log_dir = get_output_directory()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"focusguard_native_host_{today_str}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Disable logging to console in production
    logging.getLogger().handlers[1].setLevel(logging.CRITICAL)
    
    return logging.getLogger("native_host")

# --- Output Directory Setup ---
def get_output_directory() -> str:
    """Get the output directory for native host files."""
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
        output_dir = os.path.join(local_appdata, "FocusGuard")
    else:
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".focusguard")
    
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

# --- File Management ---
def get_snapshot_path() -> str:
    """Get the path for the current tab snapshot file."""
    output_dir = get_output_directory()
    username = getpass.getuser()
    pid = os.getpid()
    return os.path.join(output_dir, f"tabs_snapshot_{username}_{pid}.json")

def get_daily_snapshot_path() -> str:
    """Get the path for the daily tab snapshot file."""
    output_dir = get_output_directory()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(output_dir, f"tabs_snapshot_{today_str}.json")

def cleanup_old_files(max_age_days: int = 3):
    """Clean up old log and snapshot files."""
    output_dir = get_output_directory()
    now = datetime.datetime.now()
    logger.info("Starting cleanup of old files")
    
    # Clean up log files
    for fname in os.listdir(output_dir):
        if fname.startswith("focusguard_native_host_") and fname.endswith(".log"):
            try:
                full_path = os.path.join(output_dir, fname)
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                if (now - mtime).days > max_age_days:
                    os.remove(full_path)
                    logger.info(f"Deleted old log file: {fname}")
            except Exception as e:
                logger.error(f"Error deleting log file {fname}: {e}")
    
    # Clean up snapshot files
    for fname in os.listdir(output_dir):
        if fname.startswith("tabs_snapshot_") and fname.endswith(".json"):
            try:
                full_path = os.path.join(output_dir, fname)
                # Skip the current process's snapshot file
                if fname == os.path.basename(get_snapshot_path()):
                    continue
                    
                # Try to parse date from filename for daily snapshots
                if "_20" in fname:  # Look for year in format _YYYY-MM-DD
                    try:
                        date_part = fname.split("_")[1].split(".")[0]
                        file_date = datetime.datetime.strptime(date_part, "%Y-%m-%d")
                        if (now - file_date).days > max_age_days:
                            os.remove(full_path)
                            logger.info(f"Deleted old snapshot: {fname}")
                    except (ValueError, IndexError):
                        # If we can't parse the date, use file modification time
                        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                        if (now - mtime).days > max_age_days:
                            os.remove(full_path)
                            logger.info(f"Deleted old snapshot: {fname}")
                else:
                    # Use file modification time for other snapshot files
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                    if (now - mtime).days > max_age_days:
                        os.remove(full_path)
                        logger.info(f"Deleted old snapshot: {fname}")
            except Exception as e:
                logger.error(f"Error deleting snapshot {fname}: {e}")

# --- Process Management ---
def create_lock_file() -> bool:
    """Create a lock file to prevent multiple instances from running."""
    lock_path = os.path.join(tempfile.gettempdir(), "focusguard_native_host.lock")
    pid = os.getpid()
    timestamp = datetime.datetime.now().isoformat()
    lock_content = f"{pid},{timestamp}"
    
    try:
        # Check if lock file exists and is valid
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r") as f:
                    content = f.read().strip().split(",")
                    if len(content) >= 1:
                        old_pid = int(content[0])
                        # Check if the process is still running
                        if is_process_running(old_pid):
                            logger.warning(f"Another instance is already running with PID {old_pid}")
                            return False
                        else:
                            logger.info(f"Found stale lock file from PID {old_pid}, replacing")
            except Exception as e:
                logger.warning(f"Error reading lock file: {e}, replacing")
        
        # Create or replace the lock file
        with open(lock_path, "w") as f:
            f.write(lock_content)
        
        logger.info(f"Created lock file for PID {pid}")
        return True
    except Exception as e:
        logger.error(f"Error creating lock file: {e}")
        return False

def remove_lock_file():
    """Remove the lock file."""
    lock_path = os.path.join(tempfile.gettempdir(), "focusguard_native_host.lock")
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
            logger.info("Removed lock file")
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")

def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        if pid <= 0:
            return False
        
        if sys.platform == "win32":
            # Windows-specific implementation
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, pid)
            if handle == 0:
                return False
            kernel32.CloseHandle(handle)
            return True
        else:
            # Unix-like systems
            os.kill(pid, 0)
            return True
    except (OSError, ImportError):
        return False

def cleanup_and_exit(signum=None, frame=None):
    """Clean up resources and exit."""
    logger.info("Shutting down native messaging host")
    remove_lock_file()
    sys.exit(0)

# --- Messaging Protocol ---
def read_message() -> Dict:
    """
    Read a message from stdin according to the native messaging protocol.
    
    Returns:
        Dict: The parsed JSON message
    """
    # Read the message length (first 4 bytes as unsigned integer)
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        logger.warning("No data received from stdin, exiting")
        cleanup_and_exit()
    
    # Unpack the message length
    message_length = struct.unpack("@I", raw_length)[0]
    
    # Read the message data
    message_data = sys.stdin.buffer.read(message_length)
    
    # Parse the JSON message
    try:
        return json.loads(message_data.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON message: {e}")
        return {}

def write_message(message: Dict):
    """
    Write a message to stdout according to the native messaging protocol.
    
    Args:
        message: The message to write
    """
    # Encode the message as JSON
    encoded_message = json.dumps(message).encode("utf-8")
    
    # Write the message length (first 4 bytes)
    sys.stdout.buffer.write(struct.pack("@I", len(encoded_message)))
    
    # Write the message data
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

# --- Message Handling ---
def handle_message(message: Dict) -> Optional[Dict]:
    """
    Handle a message from the browser extension.
    
    Args:
        message: The message to handle
        
    Returns:
        Optional[Dict]: A response message, or None if no response is needed
    """
    try:
        message_type = message.get("type")
        
        if message_type == "snapshot":
            return handle_snapshot(message)
        elif message_type == "ping":
            return {"type": "pong", "timestamp": datetime.datetime.now().isoformat()}
        elif message_type == "command":
            return handle_command(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {"error": "Unknown message type"}
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

def handle_snapshot(message: Dict) -> Dict:
    """
    Handle a tab snapshot message from the browser extension.
    
    Args:
        message: The snapshot message
        
    Returns:
        Dict: A response message
    """
    try:
        tabs = message.get("tabs", [])
        browser_info = message.get("browser", {})
        browser_name = browser_info.get("name", "Unknown Browser")
        
        logger.info(f"Received tab snapshot from {browser_name} with {len(tabs)} tabs")
        
        # Create snapshot metadata
        snapshot_meta = {
            "snapshot_time": datetime.datetime.now().isoformat(),
            "timestamp": int(datetime.datetime.now().timestamp()),
            "browser": browser_info,
            "tab_count": len(tabs),
            "tabs": tabs
        }
        
        # Save to process-specific snapshot file
        snapshot_path = get_snapshot_path()
        
        # Load existing snapshots if available
        all_snapshots = {}
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    all_snapshots = json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing snapshots: {e}")
                all_snapshots = {}
        
        # Initialize browsers dictionary if needed
        if "browsers" not in all_snapshots:
            all_snapshots["browsers"] = {}
        
        # Update with new snapshot
        all_snapshots["browsers"][browser_name] = snapshot_meta
        
        # Save updated snapshots
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(all_snapshots, f, ensure_ascii=False, indent=2)
        
        # Also save to daily snapshot file
        daily_snapshot_path = get_daily_snapshot_path()
        with open(daily_snapshot_path, "w", encoding="utf-8") as f:
            json.dump(all_snapshots, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved tab snapshot to {snapshot_path} and {daily_snapshot_path}")
        
        return {"success": True, "message": "Snapshot saved"}
    except Exception as e:
        logger.error(f"Error handling snapshot: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

def handle_command(message: Dict) -> Dict:
    """
    Handle a command message from the browser extension.
    
    Args:
        message: The command message
        
    Returns:
        Dict: A response message
    """
    try:
        command = message.get("command")
        data = message.get("data", {})
        
        logger.info(f"Received command: {command} with data: {data}")
        
        # Forward the command to the application
        # This is a placeholder for actual command handling
        # In a real implementation, this would communicate with the main application
        
        return {"success": True, "message": f"Command {command} received"}
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

# --- Main ---
if __name__ == "__main__":
    # Set up logging
    logger = setup_logging()
    logger.info("FocusGuard Native Messaging Host starting up")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"User: {getpass.getuser()}")
    
    # Clean up old files
    cleanup_old_files()
    
    # Create lock file
    if not create_lock_file():
        logger.warning("Another instance is already running, exiting")
        sys.exit(0)
    
    # Register cleanup handlers
    atexit.register(remove_lock_file)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    
    # Create startup marker
    output_dir = get_output_directory()
    with open(os.path.join(output_dir, "native_host_started.txt"), "w") as f:
        f.write(f"Native host started at {datetime.datetime.now().isoformat()}\n")
    
    # Main message loop
    try:
        logger.info("Entering main message loop")
        while True:
            try:
                # Read message from stdin
                message = read_message()
                
                # Handle message
                response = handle_message(message)
                
                # Send response if needed
                if response is not None:
                    write_message(response)
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                logger.error(traceback.format_exc())
                # Continue the loop to handle the next message
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, exiting")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        cleanup_and_exit()
