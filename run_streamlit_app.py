"""
Streamlit App Runner

This script sets up the environment properly before running Streamlit
to avoid torch/asyncio compatibility issues.
"""
import os
import sys
import subprocess

# Set environment variables to disable file watching
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"

# Prepare the command to run streamlit
def run_streamlit_app():
    # Get the app path from command line or use default
    if len(sys.argv) > 1:
        app_path = sys.argv[1]
    else:
        app_path = "demos/app_classifier/demo.py"
    
    # Build the command
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.runOnSave=false"]
    
    # Add any additional arguments
    cmd.extend(sys.argv[2:])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run the streamlit app in a subprocess
    process = subprocess.Popen(cmd)
    
    try:
        # Wait for the process to complete
        process.wait()
    except KeyboardInterrupt:
        print("\nShutting down Streamlit app...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    run_streamlit_app()
