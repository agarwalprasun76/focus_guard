#!/usr/bin/env python
"""
FocusGuard Native Messaging Host
stdin  ← extension JSON messages
stdout → optional replies (not needed for tab snapshots)
"""
import sys, json, struct, pandas as pd
import getpass

def _read_msg():
    raw_len = sys.stdin.buffer.read(4)
    if not len(raw_len):
        sys.exit(0)
    msg_len = struct.unpack("<I", raw_len)[0]
    data = sys.stdin.buffer.read(msg_len)
    return json.loads(data.decode("utf-8"))

def _write_msg(obj):
    enc = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(enc)))
    sys.stdout.buffer.write(enc)
    sys.stdout.flush()

import os

# Set output directory to %LOCALAPPDATA%\FocusGuard (Windows) or cwd fallback
local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
output_dir = os.path.join(local_appdata, "FocusGuard")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, 'tabs_snapshot.json')
log_path = os.path.join(output_dir, 'focusguard_tab_log.txt')

print("Native host running as user:", getpass.getuser())
print(f"Output directory: {output_dir}")
print(f"Snapshot file: {out_path}")
print(f"Log file: {log_path}")

while True:
    msg = _read_msg()
    print(f"Received message: {msg}")  # <-- Add this
  
    if msg.get("type") == "snapshot":
        df = pd.DataFrame(msg["tabs"])
        # Log to text file (existing behavior)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(df.to_string())
            f.write("\n---\n")
        # Aggregate all browsers' snapshots in one JSON file
        import datetime
        browser_info = msg.get("browser") or {}
        browser_name = browser_info.get("name", "Unknown Browser")
        snapshot_meta = {
            "snapshot_time": datetime.datetime.now().isoformat(),
            "timestamp": int(datetime.datetime.now().timestamp()),
            "browser": browser_info,
            "tab_count": len(msg["tabs"]),
            "tabs": msg["tabs"]
        }
        # Load existing data if present
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
        print(f"Tab snapshot for {browser_name} saved to {out_path}")

        print(f"Writing log to: {log_path}")
        print(f"Writing snapshot to: {out_path}")
    else:
        _write_msg({"err": "unknown message"})
