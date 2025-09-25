"""
Run the Tab Server demo.
This script starts the Tab Server and runs the test suite.
"""
import os
import sys
import time
import threading
from core.browser_integration.tab_server_v2 import get_tab_server, stop_tab_server, is_running

def start_server():
    """Start the tab server in a separate thread."""
    print("Starting Tab Server...")
    tab_server = get_tab_server()
    tab_server.port = 5000  # Set the port before starting
    if not tab_server.start():
        print("Failed to start Tab Server. Is another instance running?")
        return False
    
    print("Tab Server started on http://127.0.0.1:5000")
    print("Endpoints:")
    print("  GET  /api/status  - Get server status")
    print("  GET  /api/tabs    - Get current tabs")
    print("  POST /api/tabs    - Update tabs (used by extension)")
    print("\nPress Ctrl+C to stop the server...")
    return True

def run_tests():
    """Run the test suite."""
    print("\nRunning tests...")
    import subprocess
    try:
        test_script = os.path.join(os.path.dirname(__file__), "test_server.py")
        subprocess.run([sys.executable, test_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        return False
    return True

def main():
    # Start the server
    if not start_server():
        return 1
    
    try:
        # Run tests after a short delay to let the server start
        time.sleep(1)
        run_tests()
        
        # Keep the server running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Tab Server...")
        stop_tab_server()
        print("Tab Server stopped.")
    except Exception as e:
        print(f"Error: {e}")
        stop_tab_server()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
