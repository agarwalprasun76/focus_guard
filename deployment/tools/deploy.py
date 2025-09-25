#!/usr/bin/env python3
"""
Focus Guard Extension Deployment - Unified Entry Point

Usage:
    python deploy.py --help
    python deploy.py developer
    python deploy.py enterprise
    python deploy.py build
"""

import sys
import argparse
import subprocess
from pathlib import Path

def run_script(script_path, *args):
    """Run a deployment script."""
    try:
        cmd = [sys.executable, script_path] + list(args)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Focus Guard Extension Deployment")
    subparsers = parser.add_subparsers(dest='command', help='Deployment commands')
    
    # Developer mode deployment
    dev_parser = subparsers.add_parser('developer', help='Deploy in developer mode')
    
    # Enterprise deployment
    ent_parser = subparsers.add_parser('enterprise', help='Deploy for enterprise')
    
    # Build CRX package
    build_parser = subparsers.add_parser('build', help='Build CRX package')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    scripts_dir = Path(__file__).parent / "scripts"
    
    if args.command == 'developer':
        print("Deploying Focus Guard in Developer Mode...")
        success = run_script(scripts_dir / "developer_deploy.py")
        
    elif args.command == 'enterprise':
        print("Deploying Focus Guard for Enterprise...")
        success = run_script(scripts_dir / "enterprise_deploy.py")
        
    elif args.command == 'build':
        print("Building Focus Guard CRX Package...")
        success = run_script(scripts_dir / "build_crx.py")
    
    if success:
        print("SUCCESS: Deployment completed successfully!")
    else:
        print("ERROR: Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
