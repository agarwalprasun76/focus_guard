#!/usr/bin/env python
"""
FocusGuard Native Messaging Host
stdin  ← extension JSON messages
stdout → optional replies (not needed for tab snapshots)
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

# --- Output Directory Setup ---
import getpass
local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
output_dir = os.path.join(local_appdata, "FocusGuard")
os.makedirs(output_dir, exist_ok=True)
username = getpass.getuser()
pid = os.getpid()
out_path = os.path.join(output_dir, f'tabs_snapshot_{username}_{pid}.json')

# --- Daily Log Rotation ---
def get_current_log_paths():
    """Get the current log paths with date-based filenames."""
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    tab_log = os.path.join(output_dir, f'focusguard_tab_log_{today_str}.txt')
    debug_log = os.path.join(output_dir, f'focusguard_debug_{today_str}.log')
    return tab_log, debug_log

# Initialize with current day's log paths
log_path, debug_log = get_current_log_paths()

# --- Logging ---
def log_debug(msg):
    try:
        # Always get the current debug log path to ensure we're using today's log file
        _, current_debug_log = get_current_log_paths()
        with open(current_debug_log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} | {msg}\n")
    except Exception as log_exc:
        pass  # Avoid recursion on logging errors


today_str = datetime.datetime.now().strftime("%Y-%m-%d")
daily_snapshot_path = os.path.join(output_dir, f"tabs_snapshot_{today_str}.json")

def delete_old_logs():
    now = datetime.datetime.now()
    for fname in os.listdir(output_dir):
        if fname.startswith("focusguard_debug") and fname.endswith(".log"):
            full_path = os.path.join(output_dir, fname)
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                if (now - mtime).days > 3:
                    os.remove(full_path)
                    log_debug(f"Deleted old log file: {fname}")
            except Exception as e:
                log_debug(f"Error deleting log {fname}: {e}")

                
def delete_old_snapshots():
    now = datetime.datetime.now()
    for fname in os.listdir(output_dir):
        if fname.startswith("tabs_snapshot_") and fname.endswith(".json"):
            try:
                full_path = os.path.join(output_dir, fname)
                date_str = fname.replace("tabs_snapshot_", "").replace(".json", "")
                file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                if (now - file_date).days > 3:
                    os.remove(full_path)
                    log_debug(f"Deleted old snapshot: {fname}")
            except Exception as e:
                log_debug(f"Error deleting snapshot {fname}: {e}")


def cleanup_temp_files():
    temp_dir = tempfile.gettempdir()
    now = datetime.datetime.now()
    for fname in os.listdir(temp_dir):
        if "focus" in fname.lower() or "guard" in fname.lower():  # conservative match
            fpath = os.path.join(temp_dir, fname)
            try:
                ctime = datetime.datetime.fromtimestamp(os.path.getctime(fpath))
                if (now - ctime).total_seconds() > 3600:  # older than 1 hour
                    if os.path.isdir(fpath):
                        os.rmdir(fpath)
                    else:
                        os.remove(fpath)
                    log_debug(f"Deleted temp file: {fpath}")
            except Exception as e:
                log_debug(f"Error deleting temp file {fname}: {e}")



log_debug("FocusGuard startup cleanup begins.")
delete_old_logs()
delete_old_snapshots()
cleanup_temp_files()
log_debug("Startup cleanup completed.")

# --- Robust Lock File to Prevent Multiple Instances ---
lock_path = os.path.join(tempfile.gettempdir(), "focus_guard.lock")


def acquire_lock():
    pid = os.getpid()
    timestamp = datetime.datetime.now().isoformat()
    lock_content = f"{pid},{timestamp}"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(lock_content)
        log_debug(f"Lock acquired (PID {pid})")
        return True
    except FileExistsError:
        # Lock file already exists
        try:
            with open(lock_path, "r") as f:
                content = f.read().strip().split(",")
                if len(content) == 2:
                    existing_pid = int(content[0])
                    if is_pid_running(existing_pid):
                        log_debug(f"Another instance already running (PID {existing_pid}). Exiting.")
                        return False
                    else:
                        log_debug(f"Stale lock detected for PID {existing_pid}. Removing stale lock.")
                        os.remove(lock_path)
                        # Try again, but only once to avoid infinite loop
                        return acquire_lock()
        except Exception as e:
            log_debug(f"Error reading/removing lock file: {e}")
            try:
                os.remove(lock_path)
            except Exception:
                pass
            return acquire_lock()
    except Exception as e:
        log_debug(f"Unexpected error acquiring lock: {e}")
        return False

def remove_lock():
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
            log_debug("Lock file removed.")
    except Exception as e:
        log_debug(f"Error removing lock file: {e}")

if not acquire_lock():
    sys.exit(0)

import atexit, signal
atexit.register(remove_lock)
signal.signal(signal.SIGTERM, lambda s, f: (remove_lock(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda s, f: (remove_lock(), sys.exit(0)))

def is_pid_running(pid):
    try:
        if pid <= 0:
            return False
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def remove_lock():
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except Exception as e:
            log_debug(f"Error removing lock file: {e}")

def cleanup_and_exit(signum=None, frame=None):
    remove_lock()
    sys.exit(0)

atexit.register(remove_lock)
signal.signal(signal.SIGTERM, cleanup_and_exit)
signal.signal(signal.SIGINT, cleanup_and_exit)

# --- Messaging ---
def _read_msg():
    raw_len = sys.stdin.buffer.read(4)
    if not len(raw_len):
        cleanup_and_exit()
    msg_len = struct.unpack("<I", raw_len)[0]
    data = sys.stdin.buffer.read(msg_len)
    return json.loads(data.decode("utf-8"))

def _write_msg(obj):
    enc = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(enc)))
    sys.stdout.buffer.write(enc)
    sys.stdout.flush()

# --- Startup Logs ---
log_debug("Native host starting up.")
log_debug(f"User: {getpass.getuser()}")
log_debug(f"Args: {sys.argv}")
log_debug(f"Environ LOCALAPPDATA: {os.environ.get('LOCALAPPDATA', '')}")

with open(os.path.join(output_dir, "native_host_started.txt"), "w") as f:
    f.write("Native host was started\n")

# --- Main Loop (Persistent) ---
try:
    while True:
        try:
            msg = _read_msg()
            log_debug(f"Received message: {msg}")
            if msg.get("type") == "snapshot":
                # Get current tab log path to ensure we're using today's log file
                current_tab_log, _ = get_current_log_paths()
                with open(current_tab_log, "a", encoding="utf-8") as f:
                    for i, tab in enumerate(msg["tabs"], 1):
                        f.write(f"Tab {i}:\n")
                        for key, val in tab.items():
                            f.write(f"  {key}: {val}\n")
                        f.write("\n")
                    f.write("---\n")
                browser_info = msg.get("browser") or {}
                browser_name = browser_info.get("name", "Unknown Browser")
                snapshot_meta = {
                    "snapshot_time": datetime.datetime.now().isoformat(),
                    "timestamp": int(datetime.datetime.now().timestamp()),
                    "browser": browser_info,
                    "tab_count": len(msg["tabs"]),
                    "tabs": msg["tabs"]
                }
                if os.path.exists(out_path):
                    try:
                        with open(out_path, 'r', encoding='utf-8') as f:
                            all_snapshots = json.load(f)
                    except Exception:
                        all_snapshots = {}
                else:
                    all_snapshots = {}
                if "browsers" not in all_snapshots:
                    all_snapshots["browsers"] = {}
                all_snapshots["browsers"][browser_name] = snapshot_meta
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(all_snapshots, f, ensure_ascii=False, indent=2)
                # Get current log paths
                current_tab_log, _ = get_current_log_paths()
                log_debug(f"Tab snapshot for {browser_name} saved to {out_path}")
                log_debug(f"Writing log to: {current_tab_log}")
                log_debug(f"Writing snapshot to: {out_path}")
            else:
                _write_msg({"err": "unknown message"})
        except Exception as e:
            log_debug(f"Exception in message handling: {traceback.format_exc()}")
            break
except Exception as e:
    log_debug(f"Fatal error: {traceback.format_exc()}")
    remove_lock()
    sys.exit(1)
